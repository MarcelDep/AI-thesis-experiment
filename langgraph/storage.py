
import json
import os
from datetime import datetime, timezone

from dotenv import load_dotenv
from supabase import create_client

from langchain_core.messages import (
    convert_to_messages,
    messages_from_dict,
    messages_to_dict,
)

import schemas


# ---------------------------------------------------------- connection --

load_dotenv(".supabase_creds")

supabase = create_client(
    os.environ["SUPABASE_URL"],
    os.environ["SUPABASE_KEY"],
)


# ---------------------------------------------------------- serialization --

def _dump(model):
    if hasattr(model, "model_dump"):
        return model.model_dump()
    return model or {}


def state_to_json(state):
    """Graph state -> JSON-compatible dictionary."""

    return {
        "messages": messages_to_dict(
            convert_to_messages(state.get("messages", []))
        ),
        "choosed_agent": state.get("choosed_agent", ""),
        "interview_state": _dump(state.get("interview_state")),
        "planner_state": _dump(state.get("planner_state")),
        "tracking_state": _dump(state.get("tracking_state")),
    }


def state_from_json(raw):
    """JSON-compatible dictionary -> Graph state."""

    d = raw or {}

    return {
        "messages": messages_from_dict(d.get("messages", [])),
        "conv_summary": [],
        "choosed_agent": d.get("choosed_agent", ""),
        "update_state": False,
        "interview_state": schemas.InterviewState.model_validate(
            d.get("interview_state", {})
        ),
        "planner_state": schemas.PlannerState.model_validate(
            d.get("planner_state", {})
        ),
        "tracking_state": schemas.TrackingState.model_validate(
            d.get("tracking_state", {})
        ),
        "github_variables": schemas.GithubVariables(),
    }


# ---------------------------------------------------------- operations --

def save_conversation(conv_id, email, chat, state):
    """Creates or updates a conversation. Returns conversation ID."""

    now = datetime.now(timezone.utc).isoformat(timespec="seconds")

    first_user = next(
        (m["content"] for m in chat if m["role"] == "user"),
        "New conversation",
    )

    title = " ".join(first_user.split())[:50] or "New conversation"

    payload = {
        "chat_json": chat,
        "state_json": state_to_json(state),
        "updated_at": now,
    }

    if conv_id is not None:
        response = (
            supabase.table("conversations")
            .update(payload)
            .eq("id", conv_id)
            .eq("user_email", email)
            .execute()
        )

        if response.data:
            return conv_id

    payload.update({
        "user_email": email,
        "title": title,
        "created_at": now,
    })

    response = (
        supabase.table("conversations")
        .insert(payload)
        .execute()
    )

    return response.data[0]["id"]


def list_conversations(email, limit=30):
    response = (
        supabase.table("conversations")
        .select("id, title, updated_at")
        .eq("user_email", email)
        .order("updated_at", desc=True)
        .limit(limit)
        .execute()
    )

    return response.data


def load_conversation(conv_id, email):
    """Returns (chat, state) or None."""

    response = (
        supabase.table("conversations")
        .select("chat_json, state_json")
        .eq("id", conv_id)
        .eq("user_email", email)
        .limit(1)
        .execute()
    )

    if not response.data:
        return None

    row = response.data[0]

    return (
        row["chat_json"],
        state_from_json(row["state_json"]),
    )


def remove_account(actor_role, target_user_id):
    """Deletes a user's conversations and Supabase Auth account."""

    if actor_role != "admin":
        return "Invalid role - you cannot remove other accounts."

    try:
        user = supabase.auth.admin.get_user_by_id(target_user_id)

        if not user or not user.user:
            return "User not found."

        target_email = user.user.email

        supabase.table("conversations") \
            .delete() \
            .eq("user_email", target_email) \
            .execute()

        supabase.auth.admin.delete_user(target_user_id)

        return "User account and conversations deleted successfully."

    except Exception as e:
        return f"Error deleting account: {str(e)}"