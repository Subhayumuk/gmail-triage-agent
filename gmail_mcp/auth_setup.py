"""
One-time interactive Gmail authorization.

Run this manually, once, from a machine with a browser:
    python gmail_mcp/auth_setup.py

It opens a browser, asks you to log in to Google and approve access, then
saves a refresh token to token.json. After that, the MCP server (and any
headless/scheduled run) can refresh the token on its own — no browser needed
again unless you revoke access or delete token.json.
"""
import os

from google_auth_oauthlib.flow import InstalledAppFlow

from gmail_auth import CREDENTIALS_PATH, SCOPES, TOKEN_PATH


def main():
    if not os.path.exists(CREDENTIALS_PATH):
        raise FileNotFoundError(
            f"Missing {CREDENTIALS_PATH}. Download the OAuth client credentials JSON from "
            "Google Cloud Console (APIs & Services > Credentials) and save it there as credentials.json."
        )

    flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
    creds = flow.run_local_server(port=0)

    with open(TOKEN_PATH, "w") as f:
        f.write(creds.to_json())

    print(f"Authorized. Token saved to {TOKEN_PATH}.")


if __name__ == "__main__":
    main()
