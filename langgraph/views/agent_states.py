import streamlit as st

from ui_common import to_dict, md_table

STATUS_ICON = {"done": "✅", "in_progress": "🔄", "not_started": "⬜"}
REQUIRED_FIELDS = ["goal", "technologies", "deadline", "working_style", "requirements"]


def render_interview(state):
    data = to_dict(state.get("interview_state"))
    filled = sum(1 for f in REQUIRED_FIELDS if data.get(f))
    st.progress(filled / len(REQUIRED_FIELDS), text=f"{filled}/{len(REQUIRED_FIELDS)} required fields filled")
    md_table([{"Field": k, "Value": v or "—"} for k, v in data.items()])


def render_planner(state):
    data = to_dict(state.get("planner_state"))
    general, specific = data.get("general_plan", []), data.get("specific_plan", [])
    if not general and not specific:
        st.info("No plan yet.")
        return
    if general:
        st.markdown("**General plan (phases)**")
        md_table(general)
    if specific:
        tasks = [t for phase in specific for t in phase.get("tasks", [])]
        done = sum(1 for t in tasks if t.get("status") == "done")
        if tasks:
            st.progress(done / len(tasks), text=f"{done}/{len(tasks)} tasks done")
        st.markdown("**Specific plan (tasks)**")
        for phase in specific:
            with st.expander(f"Phase {phase.get('phase_id')}: {phase.get('phase_name')}", expanded=True):
                md_table([
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
        md_table([
            {"SHA": (c.get("commit_sha") or "")[:7], "Message": c.get("commit_message")}
            for c in commits
        ])
    if data.get("last_diff"):
        with st.expander("Last fetched diff"):
            st.code(data["last_diff"], language="diff")


state = st.session_state.graph_state

st.title("Agent states")
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