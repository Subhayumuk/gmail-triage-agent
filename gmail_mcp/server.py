"""
Minimal local MCP server exposing Gmail as tools for Claude Code.

Register it once with:
    claude mcp add gmail -- python "<full path to this file>"

Then Claude Code (interactive or headless `-p`) can call these tools directly
instead of shelling out to scripts and parsing text output.
"""
import base64
from typing import Optional

from mcp.server.mcpserver import MCPServer

from gmail_auth import get_gmail_service

mcp = MCPServer("gmail-triage")

_label_cache: dict[str, str] = {}


def _extract_body(payload: dict) -> str:
    """Walk a Gmail message payload and return the first text/plain part as a string."""
    if payload.get("mimeType") == "text/plain" and payload.get("body", {}).get("data"):
        data = payload["body"]["data"]
        return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")

    for part in payload.get("parts", []) or []:
        text = _extract_body(part)
        if text:
            return text

    return ""


def _get_or_create_label(service, label_name: str) -> str:
    if label_name in _label_cache:
        return _label_cache[label_name]

    labels = service.users().labels().list(userId="me").execute().get("labels", [])
    for label in labels:
        if label["name"].lower() == label_name.lower():
            _label_cache[label_name] = label["id"]
            return label["id"]

    created = service.users().labels().create(
        userId="me",
        body={"name": label_name, "labelListVisibility": "labelShow", "messageListVisibility": "show"},
    ).execute()
    _label_cache[label_name] = created["id"]
    return created["id"]


@mcp.tool()
def list_recent_emails(max_results: int = 20, query: str = "in:inbox is:unread") -> list[dict]:
    """
    List recent emails matching a Gmail search query.

    Default query is unread inbox mail. Use standard Gmail search syntax,
    e.g. "in:inbox newer_than:1d" to scope to the last day.
    """
    service = get_gmail_service()
    results = service.users().messages().list(userId="me", q=query, maxResults=max_results).execute()
    messages = results.get("messages", [])

    out = []
    for m in messages:
        msg = service.users().messages().get(
            userId="me", id=m["id"], format="metadata",
            metadataHeaders=["From", "Subject", "Date"],
        ).execute()
        headers = {h["name"]: h["value"] for h in msg["payload"]["headers"]}
        out.append({
            "id": m["id"],
            "from": headers.get("From", ""),
            "subject": headers.get("Subject", ""),
            "date": headers.get("Date", ""),
            "snippet": msg.get("snippet", ""),
        })
    return out


@mcp.tool()
def get_email_body(message_id: str) -> str:
    """Get the plain-text body of a single email by its Gmail message id."""
    service = get_gmail_service()
    msg = service.users().messages().get(userId="me", id=message_id, format="full").execute()
    body = _extract_body(msg["payload"])
    return body or msg.get("snippet", "")


@mcp.tool()
def apply_label(message_id: str, label_name: str) -> str:
    """Apply a Gmail label to a message, creating the label first if it doesn't exist."""
    service = get_gmail_service()
    label_id = _get_or_create_label(service, label_name)
    service.users().messages().modify(
        userId="me", id=message_id, body={"addLabelIds": [label_id]},
    ).execute()
    return f"Applied label '{label_name}' to message {message_id}"


@mcp.tool()
def star_email(message_id: str) -> str:
    """Star an email in Gmail (marks it important)."""
    service = get_gmail_service()
    service.users().messages().modify(
        userId="me", id=message_id, body={"addLabelIds": ["STARRED"]},
    ).execute()
    return f"Starred message {message_id}"


@mcp.tool()
def mark_as_read(message_id: str) -> str:
    """Mark an email as read."""
    service = get_gmail_service()
    service.users().messages().modify(
        userId="me", id=message_id, body={"removeLabelIds": ["UNREAD"]},
    ).execute()
    return f"Marked message {message_id} as read"


if __name__ == "__main__":
    mcp.run()
