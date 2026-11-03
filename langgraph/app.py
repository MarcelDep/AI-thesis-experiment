"""
Entrypoint of the multipage app.  Run:  streamlit run app.py

Files (put them next to graph.py and schemas.py):
    app.py                  <- this file: navigation, sidebar (login status, history, GitHub)
    ui_common.py            <- shared helpers (session, running the graph, saving)
    storage.py              <- SQLite conversation history (creates app.db, add it to .gitignore)
    views/login.py, chat.py, agent_states.py, agent_trace.py, about.py

All pages (Chat, Agent states, Agent trace, About) are open to guests, but nothing they write is
saved. Logged-in users additionally get saved history and the GitHub inputs.
"""
import streamlit as st
from dotenv import load_dotenv
from datetime import datetime, timezone

load_dotenv()

import storage
import ui_common as ui

st.set_page_config(page_title="Project Management Agent", layout="wide")

ui.init_session()


def log_out():
    ui.reset_conversation()
    st.logout()

supabase = storage.supabase

dt = datetime.now(timezone.utc).isoformat()

logged_in = st.user.is_logged_in
busy = st.session_state.busy

chat_page = st.Page("views/chat.py", title="Chat", icon="💬", default=True)
states_page = st.Page("views/agent_states.py", title="Agent states", icon="📁")
trace_page = st.Page("views/agent_trace.py", title="Agent trace", icon="🔍")
about_page = st.Page("views/about.py", title="About", icon="ℹ️")
login_page = st.Page("views/login.py", title="Log in")
users_page = st.Page("views/admin/users.py", title="Users")

details = [states_page, trace_page, about_page]
admin_panel = [users_page,]

if logged_in:
    email = st.user.email
    user_response = (
        supabase.table("users")
        .select("role")
        .eq("email", email)
        .execute()
    )

    if user_response.data:
        role = user_response.data[0]["role"]

        supabase.table("users").update({
            "last_login": dt
        }).eq("email", email).execute()

    else:
        supabase.table("users").insert({
            "email": email,
            "role": "user",
            "created_at": dt,
            "last_login": dt
        }).execute()

        role = "user"

    if role == "admin":
        pg = st.navigation({
            "Home": [chat_page],
            "Details": details,
            "Admin panel": admin_panel
        })
    else:
        pg = st.navigation({
            "Home": [chat_page],
            "Details": details,
        })

else:
    pg = st.navigation({
        "Home": [chat_page],
        "Details": details,
        "Account": [login_page],
    })

with st.sidebar:
    if logged_in:
        st.success(f"✅ Logged in as **{email}**")
        st.button("Log out", on_click=log_out, disabled=busy)
    else:
        st.info("👤 Guest mode: your conversation is not saved. Log in to keep your history.")
        st.button("Log in with Google", on_click=st.login, disabled=busy)

    st.divider()
    if st.button("➕ New conversation", disabled=busy, use_container_width=True):
        ui.reset_conversation()
        st.rerun()

    if logged_in:
        st.subheader("History")
        conversations = storage.list_conversations(ui.current_email())
        if not conversations:
            st.caption("No saved conversations yet.")
        for conv in conversations:
            is_current = conv["id"] == st.session_state.conv_id
            label = f"{conv['title']}  ·  {conv['updated_at'][:10]}"
            if st.button(
                label,
                key=f"conv_{conv['id']}",
                type="primary" if is_current else "secondary",
                use_container_width=True,
                disabled=busy,
            ):
                ui.load_conversation(conv["id"])
                st.rerun()

        st.divider()
        st.subheader("GitHub")
        st.text_input("GitHub repo", key="gh_repo", disabled=busy)
        st.text_input("GitHub owner", key="gh_owner", disabled=busy)
        st.caption("The token is read from GITHUB_PAT in the .env file.")
    else:
        st.caption("GitHub tools are available after logging in.")

pg.run()