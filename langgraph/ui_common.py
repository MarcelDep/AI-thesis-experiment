"""Shared helpers for all pages. No Streamlit commands are executed at import time."""
import contextlib
import sys

import streamlit as st

import schemas
import storage
import graph as graph_module

graph = graph_module.graph


# ------------------------------------------------------------------ helpers --
class Tee:
    """Copies everything written to stdout into a buffer (and still prints to the terminal)."""

    def __init__(self, real):
        self._real = real
        self._buf = []

    def write(self, s):
        self._real.write(s)
        self._buf.append(s)
        return len(s)

    def flush(self):
        self._real.flush()

    def __getattr__(self, name):
        return getattr(self._real, name)

    def drain(self):
        text, self._buf = "".join(self._buf), []
        return [line for line in text.splitlines() if line.strip()]


def to_dict(obj):
    """State fields can be pydantic objects or plain dicts, handle both."""
    if obj is None:
        return {}
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if isinstance(obj, dict):
        return obj
    return {}


def message_text(msg):
    content = getattr(msg, "content", msg)
    if isinstance(content, list):
        content = "".join(p.get("text", "") if isinstance(p, dict) else str(p) for p in content)
    return str(content)


def md_table(rows):
    """Markdown table without pandas (st.table / st.dataframe go through pandas, which segfaulted here)."""
    if not rows:
        return
    headers = list(rows[0].keys())

    def cell(v):
        return str("" if v is None else v).replace("|", "\\|").replace("\n", " ")

    lines = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    for r in rows:
        lines.append("| " + " | ".join(cell(r.get(h)) for h in headers) + " |")
    st.markdown("\n".join(lines))


def current_email():
    """E-mail of the logged-in user, or None for a guest."""
    if st.user.is_logged_in and st.user.email:
        return st.user.email.lower()
    return None


# ------------------------------------------------------------------ session --
def initial_state():
    return {
        "messages": [],
        "conv_summary": [],
        "choosed_agent": "",
        "update_state": False,
        "interview_state": schemas.InterviewState(),
        "planner_state": schemas.PlannerState(),
        "tracking_state": schemas.TrackingState(),
        "github_variables": schemas.GithubVariables(),
    }

def init_session():
    """Called once per run from app.py."""
    st.session_state.setdefault("busy", False)
    st.session_state.setdefault("pending", None)
    st.session_state.setdefault("gh_repo", "")
    st.session_state.setdefault("gh_owner", "")
    st.session_state.setdefault("conv_id", None)

    if "graph_state" not in st.session_state:
        st.session_state.graph_state = initial_state()
        st.session_state.chat = []
        st.session_state.trace = []


def _clear_inner_agent_memory():
    # the inner agents keep their own history in a checkpointer (best-effort clean-up)
    try:
        thread_id = graph_module.agents.thread_config["configurable"]["thread_id"]
        for agent in (graph_module.interview, graph_module.planner, graph_module.tracking):
            agent.agent.checkpointer.delete_thread(thread_id)
    except Exception:
        pass


def reset_conversation():
    """Starts a new, empty conversation (the old one stays in the history)."""
    st.session_state.graph_state = initial_state()
    st.session_state.chat = []
    st.session_state.trace = []
    st.session_state.conv_id = None
    _clear_inner_agent_memory()


def load_conversation(conv_id):
    """Opens a saved conversation of the logged-in user."""
    email = current_email()
    if not email:
        return
    row = storage.load_conversation(conv_id, email)
    if row is None:
        return
    chat, state = row
    st.session_state.chat = chat
    st.session_state.graph_state = state
    st.session_state.trace = []
    st.session_state.conv_id = conv_id
    _clear_inner_agent_memory()


# ---------------------------------------------------------------- graph run --
def describe_node(node, update):
    text = f"node '{node}' finished"
    if isinstance(update, dict):
        if update:
            text += f" (updated: {', '.join(update.keys())})"
        if node == "router" and update.get("choosed_agent"):
            text += f" -> router chose {update['choosed_agent']}"
    return text


def run_turn(user_text):
    """Runs the graph for one user message, appends the reply to the chat and saves it (logged-in users)."""
    turn_no = len(st.session_state.trace) + 1

    state = dict(st.session_state.graph_state)          # copy: the stored state changes only on success
    state["messages"] = list(state.get("messages", [])) + [{"role": "user", "content": user_text}]
    gh = to_dict(state.get("github_variables"))
    state["github_variables"] = schemas.GithubVariables(
        **{**gh, "repo": st.session_state.gh_repo, "owner": st.session_state.gh_owner}
    )

    events, final = [], None
    tee = Tee(sys.stdout)
    try:
        with contextlib.redirect_stdout(tee):
            for mode, data in graph.stream(state, stream_mode=["updates", "values"]):
                if mode == "values":
                    final = data
                    continue
                # a node has just finished: first its console output, then the node event
                events += [("log", line) for line in tee.drain()]
                for node, update in data.items():
                    events.append(("node", describe_node(node, update)))
    except Exception as exc:
        events += [("log", line) for line in tee.drain()]
        events.append(("error", f"{type(exc).__name__}: {exc}"))
        final = None
    events += [("log", line) for line in tee.drain()]

    st.session_state.trace.append({"turn": turn_no, "user": user_text, "events": events})

    if final is None:
        reply = "⚠️ Something went wrong. Details are on the **Agent trace** page."
    else:
        st.session_state.graph_state = final
        reply = message_text(final["messages"][-1])
    st.session_state.chat.append({"role": "assistant", "content": reply})

    email = current_email()
    if email:                                            # guests are not saved
        try:
            st.session_state.conv_id = storage.save_conversation(
                st.session_state.conv_id, email, st.session_state.chat, st.session_state.graph_state
            )
        except Exception as exc:                         # a storage problem must not break the chat
            print(f"----storage could not save the conversation: {exc}")