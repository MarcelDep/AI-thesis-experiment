"""
Streamlit UI for the multi-agent project management graph.
Put this file next to graph.py and run:  streamlit run app.py

Tabs: Chat | Agent states | Agent trace | About
Sidebar: GitHub repo/owner + "New conversation".
"""
import contextlib
import sys
import streamlit as st
from dotenv import load_dotenv

load_dotenv()  # before importing graph: models and tools read env variables at import time

import schemas
import graph as graph_module

st.set_page_config(page_title="Project Management Agent", page_icon="🗂️", layout="wide")

st.session_state.setdefault("busy", False)
st.session_state.setdefault("pending", None)

graph = graph_module.graph

STATUS_ICON = {"done": "✅", "in_progress": "🔄", "not_started": "⬜"}
REQUIRED_FIELDS = ["goal", "technologies", "deadline", "working_style", "requirements"]

ABOUT_MD = """
## Bezpieczny system wieloagentowy wspomagający zarządzanie projektami programistycznymi

Aplikacja powstaje w ramach pracy inżynierskiej.

### Cel
Zautomatyzowanie planowania projektu i monitorowania jego postępu, tak aby programista
mógł poświęcić czas na część techniczną, a nie na zarządzanie. Aplikacja jest skierowana do osób
z branży IT, a w szczególności do studentów, którzy realizują projekt w nieznanej im dziedzinie
i potrzebują jasno określonych zadań.

### Jak to działa
1. **Router** wybiera agenta, który ma odpowiedzieć na wiadomość użytkownika.
2. **Interview agent** przeprowadza wywiad i ustala cel, region, termin, technologie, wymagania i styl pracy.
3. **Planner agent** na podstawie wywiadu tworzy plan ogólny (fazy) i szczegółowy (zadania w fazach).
4. **Tracking agent** pobiera commity z GitHuba i na ich podstawie aktualizuje statusy zadań.

### Funkcjonalności
- rozmowa z agentami w jednym oknie czatu,
- automatyczne tworzenie planu projektu z fazami i zadaniami,
- weryfikacja postępu na podstawie commitów i zmian w kodzie (diff),
- podgląd stanu każdego agenta oraz śladu jego działania (wybór agenta, użyte narzędzia).

### Bezpieczeństwo
- każdy agent ma przypisaną własną, ograniczoną listę narzędzi (zasada najmniejszych uprawnień),
- poświadczenia GitHub są czytane ze zmiennych środowiskowych, a nie przechowywane w stanie aplikacji,
- uwierzytelnianie OAuth2 i kontrola dostępu RBAC: w trakcie realizacji.

### Stos technologiczny
Python, LangGraph / LangChain, Gemini API, Streamlit, GitHub REST API, Pydantic.

### Ograniczenia
Jedynym źródłem informacji o postępie jest repozytorium GitHub, a jakość statusów zależy od
komunikatów commitów i od modelu językowego. Aplikacja jest prototypem demonstracyjnym.
"""


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


def reset_conversation():
    st.session_state.graph_state = initial_state()
    st.session_state.chat = []
    st.session_state.trace = []
    # the inner agents keep their own history in a checkpointer (best-effort clean-up)
    try:
        thread_id = graph_module.agents.thread_config["configurable"]["thread_id"]
        for agent in (graph_module.interview, graph_module.planner, graph_module.tracking):
            agent.agent.checkpointer.delete_thread(thread_id)
    except Exception:
        pass


def describe_node(node, update):
    text = f"node '{node}' finished"
    if isinstance(update, dict):
        if update:
            text += f" (updated: {', '.join(update.keys())})"
        if node == "router" and update.get("choosed_agent"):
            text += f" -> router chose {update['choosed_agent']}"
    return text


def run_turn(user_text):
    """Runs the graph for one user message. Returns the reply text, or None on error."""
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
        return None
    st.session_state.graph_state = final
    return message_text(final["messages"][-1])


def event_icon(kind, text):
    if kind == "node":
        return "▶️"
    if kind == "error":
        return "❌"
    for prefix, icon in (("----ROUTER", "🧭"), ("----AGENT", "🤖"), ("----EXTRACTION", "🧾"), ("----TOOL", "🔧")):
        if text.startswith(prefix):
            return icon
    return "·"


# ---------------------------------------------------------- state renderers --
def render_interview(state):
    data = to_dict(state.get("interview_state"))
    filled = sum(1 for f in REQUIRED_FIELDS if data.get(f))
    st.progress(filled / len(REQUIRED_FIELDS), text=f"{filled}/{len(REQUIRED_FIELDS)} required fields filled")
    st.table([{"Field": k, "Value": v or "—"} for k, v in data.items()])


def render_planner(state):
    data = to_dict(state.get("planner_state"))
    general, specific = data.get("general_plan", []), data.get("specific_plan", [])
    if not general and not specific:
        st.info("No plan yet.")
        return
    if general:
        st.markdown("**General plan (phases)**")
        st.dataframe(general, hide_index=True, use_container_width=True)
    if specific:
        tasks = [t for phase in specific for t in phase.get("tasks", [])]
        done = sum(1 for t in tasks if t.get("status") == "done")
        if tasks:
            st.progress(done / len(tasks), text=f"{done}/{len(tasks)} tasks done")
        st.markdown("**Specific plan (tasks)**")
        for phase in specific:
            with st.expander(f"Phase {phase.get('phase_id')}: {phase.get('phase_name')}", expanded=True):
                st.table([
                    {
                        "ID": t.get("task_id"),
                        "Task": t.get("task_name"),
                        "Deadline": t.get("deadline") or "—",
                        "Status": f"{STATUS_ICON.get(t.get('status'), '')} {t.get('status')}",
                    }
                    for t in phase.get("tasks", [])
                ])


def render_tracking(state):
    data = to_dict(state.get("tracking_state"))
    commits = data.get("commits_msg_sha", [])
    if not commits and not data.get("last_diff"):
        st.info("No commit data yet.")
        return
    if commits:
        st.markdown("**Fetched commits**")
        st.table([
            {"SHA": (c.get("commit_sha") or "")[:7], "Message": c.get("commit_message")}
            for c in commits
        ])
    if data.get("last_diff"):
        with st.expander("Last fetched diff"):
            st.code(data["last_diff"], language="diff")


# --------------------------------------------------------------- session ----
if "graph_state" not in st.session_state:
    st.session_state.graph_state = initial_state()
    st.session_state.chat = []
    st.session_state.trace = []

with st.sidebar:
    st.header("GitHub")
    st.text_input("GitHub repo", key="gh_repo", disabled=st.session_state.busy)
    st.text_input("GitHub owner", key="gh_owner", disabled=st.session_state.busy)
    st.caption("The token is read from GITHUB_PAT in the .env file.")
    st.divider()
    if st.button("New conversation", disabled=st.session_state.busy):
        reset_conversation()
        st.rerun()

st.title("Project Management Agent")

# chat_input at top level, so it stays pinned to the bottom of the page
prompt = st.chat_input("Type your message", disabled=st.session_state.busy)
if prompt and not st.session_state.busy:
    st.session_state.chat.append({"role": "user", "content": prompt})
    st.session_state.pending = prompt
    st.session_state.busy = True
    st.rerun()

tab_chat, tab_states, tab_trace, tab_about = st.tabs(
    ["💬 Chat", "🗂️ Agent states", "🧠 Agent trace", "ℹ️ About"]
)

with tab_chat:
    if not st.session_state.chat:
        st.caption("Say hello to start the interview.")
    for msg in st.session_state.chat:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
    chat_status = st.container()

with tab_states:
    state = st.session_state.graph_state
    st.caption(f"Last agent chosen by the router: **{state.get('choosed_agent') or '—'}**")
    st.subheader("Interview agent")
    render_interview(state)
    st.subheader("Planner agent")
    render_planner(state)
    st.subheader("Tracking agent")
    render_tracking(state)
    with st.expander("Raw state (JSON)"):
        st.json({
            "interview_state": to_dict(state.get("interview_state")),
            "planner_state": to_dict(state.get("planner_state")),
            "tracking_state": to_dict(state.get("tracking_state")),
        })

with tab_trace:
    if not st.session_state.trace:
        st.info("No activity yet. Send a message in the Chat tab.")
    for i, turn in enumerate(reversed(st.session_state.trace)):
        with st.expander(f"Turn {turn['turn']}: {turn['user'][:70]}", expanded=(i == 0)):
            for kind, text in turn["events"]:
                st.text(f"{event_icon(kind, text)} {text.lstrip('-')}")

with tab_about:
    st.markdown(ABOUT_MD)

if st.session_state.busy and st.session_state.pending:
    try:
        with chat_status:
            with st.spinner("Agents are working..."):
                reply = run_turn(st.session_state.pending)
        if reply is None:
            reply = "⚠️ Something went wrong. Details are in the **Agent trace** tab."
        st.session_state.chat.append({"role": "assistant", "content": reply})
    finally:
        st.session_state.busy = False
        st.session_state.pending = None
    st.rerun()