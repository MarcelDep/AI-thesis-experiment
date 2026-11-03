from auth import require_role
import storage
import streamlit as st
import pandas as pd

require_role("admin")

st.title("Admin panel")

supabase = storage.supabase

users_response = (
    supabase.table("users")
    .select("*")
    .execute()
)

users_data = users_response.data

if users_data:
    df = pd.DataFrame(users_data)

    st.subheader("Change user role")

    edited_df = st.data_editor(
        df,
        use_container_width=True,
        hide_index=True,
        disabled=["email", "created_at", "last_login"],
        column_config={
            "email": st.column_config.TextColumn("Email"),
            "role": st.column_config.SelectboxColumn(
                "Role",
                options=["user", "admin"],
                required=True
            ),
            "created_at": st.column_config.TextColumn("Created at"),
            "last_login": st.column_config.TextColumn("Last login"),
        },
        key="users_editor"
    )

    if st.button("Zapisz zmiany"):
        changes_count = 0

        for index, row in edited_df.iterrows():
            old_role = df.loc[index, "role"]
            new_role = row["role"]

            if old_role != new_role:
                supabase.table("users").update(
                    {"role": new_role}
                ).eq("email", row["email"]).execute()

                changes_count += 1

        if changes_count > 0:
            st.success(f"Zapisano zmiany dla {changes_count} użytkowników.")
            st.rerun()
        else:
            st.info("Nie wprowadzono żadnych zmian.")

    st.divider()

    st.subheader("Delete user")

    selected_email = st.selectbox(
        "Wybierz użytkownika do usunięcia",
        options=[user["email"] for user in users_data],
        key="delete_user_select"
    )

    selected_user = next(
        user for user in users_data
        if user["email"] == selected_email
    )

    if selected_user["role"] == "admin":
        st.warning("Wybrany użytkownik jest administratorem.")

    confirm_delete = st.checkbox(
        f"Potwierdzam usunięcie użytkownika {selected_email}",
        key="confirm_delete"
    )

    if st.button(
        "Usuń użytkownika",
        type="primary",
        disabled=not confirm_delete
    ):

        admins_response = (
            supabase.table("users")
            .select("email")
            .eq("role", "admin")
            .execute()
        )

        admins_count = len(admins_response.data)

        if selected_user["role"] == "admin" and admins_count <= 1:
            st.error("Nie można usunąć ostatniego administratora!")

        else:
            supabase.table("conversations").delete().eq(
                "user_email", selected_email
            ).execute()

            supabase.table("users").delete().eq(
                "email", selected_email
            ).execute()

            st.success(f"Użytkownik {selected_email} został usunięty.")
            st.rerun()

else:
    st.info("Brak użytkowników w bazie.")