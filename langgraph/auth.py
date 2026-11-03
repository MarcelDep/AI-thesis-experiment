
import streamlit as st
import storage

def get_user_role():
    if not st.user.is_logged_in:
        return "guest"

    email = st.user.email

    response = (
        storage.supabase.table("users")
        .select("role")
        .eq("email", email)
        .execute()
    )

    if not response.data:
        return "user"

    return response.data[0]["role"]


def require_role(required_role):
    role = get_user_role()

    if required_role == "admin" and role != "admin":
        st.error("Access denied. Admin privileges required.")
        st.stop()

    if required_role == "user" and role == "guest":
        st.error("Access denied. User or admin privileges required.")
        st.stop()

    if require_role == "guest":
        pass

    return role