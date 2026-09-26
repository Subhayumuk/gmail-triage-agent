"""
Shared Gmail authentication helper.

Loads the OAuth token saved by auth_setup.py, refreshing it automatically
when it expires. Both the one-time setup script and the MCP server import
this so there's only one place that knows how credentials are stored.
"""
import os

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

# gmail.modify = read + label + star, but NOT permanent delete or sending.
# Kept narrow on purpose: this agent only needs to read and organize mail.
SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CREDENTIALS_PATH = os.path.join(BASE_DIR, "credentials.json")
TOKEN_PATH = os.path.join(BASE_DIR, "token.json")


def get_gmail_service():
    if not os.path.exists(TOKEN_PATH):
        raise RuntimeError(
            f"No token found at {TOKEN_PATH}. Run 'python gmail_mcp/auth_setup.py' "
            "once (with a browser available) to authorize this app against your Gmail account."
        )

    creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(TOKEN_PATH, "w") as f:
            f.write(creds.to_json())

    return build("gmail", "v1", credentials=creds)
