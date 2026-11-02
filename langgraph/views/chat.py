import streamlit as st

import ui_common as ui

st.title("Project Management Agent")

# chat_input at page level, so it stays pinned to the bottom of the page
prompt = st.chat_input("Type your message", disabled=st.session_state.busy)
if prompt and not st.session_state.busy:
    st.session_state.chat.append({"role": "user", "content": prompt})
    st.session_state.pending = prompt
    st.session_state.busy = True
    st.rerun()   # the next run renders the input already disabled

if not st.session_state.chat:
    st.caption("Say hello to start the interview.")
for msg in st.session_state.chat:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
chat_status = st.container()

if st.session_state.busy and st.session_state.pending:
    try:
        with chat_status:
            with st.spinner("Agents are working..."):
                ui.run_turn(st.session_state.pending)
    finally:
        st.session_state.busy = False     # always unlock, also after an error
        st.session_state.pending = None
    st.rerun()