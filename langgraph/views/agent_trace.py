import streamlit as st

st.title("Agent trace")

if not st.session_state.trace:
    st.info("No activity yet. Send a message on the Chat page.")

for i, turn in enumerate(reversed(st.session_state.trace)):
    with st.expander(f"Turn {turn['turn']}: {turn['user'][:70]}", expanded=(i == 0)):
        for kind, text in turn["events"]:
            line = text.lstrip("-").strip()
            st.text(f"ERROR: {line}" if kind == "error" else line)