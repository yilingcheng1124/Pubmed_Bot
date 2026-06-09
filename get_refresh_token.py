"""
One-time LOCAL helper to obtain a Google Drive OAuth refresh token for Branch C.

This is NOT run by the bot / GitHub Actions. You run it once on your own machine,
sign in with the Google account whose Drive holds your Obsidian vault, and copy the
four values it prints into your GitHub repository Secrets.

Prerequisites
-------------
1. In Google Cloud Console (you can reuse the project you already made):
   - APIs & Services -> Library -> enable "Google Drive API".
   - APIs & Services -> OAuth consent screen -> User type "External" ->
     add your own Gmail under "Test users".
   - APIs & Services -> Credentials -> Create credentials -> OAuth client ID ->
     Application type "Desktop app" -> Create.
   - Download the JSON and save it next to this script as "client_secret.json"
     (or just have the client_id / client_secret ready to paste).
2. Install the one extra dependency locally (only needed for this helper):
       pip install google-auth-oauthlib

Run
---
    python get_refresh_token.py

A browser window opens; sign in and approve. The refresh token is printed at the end.
"""

import os
import json

try:
    from google_auth_oauthlib.flow import InstalledAppFlow
except ImportError:
    raise SystemExit(
        "Missing dependency. Run:  pip install google-auth-oauthlib"
    )

# drive.file = least privilege: the app can only see/manage files it creates,
# which is exactly what Branch C needs (it writes new notes into your vault folder).
SCOPES = ["https://www.googleapis.com/auth/drive.file"]

CLIENT_SECRET_FILE = "client_secret.json"


def build_client_config():
    """Load the OAuth client from client_secret.json, or fall back to manual entry."""
    if os.path.exists(CLIENT_SECRET_FILE):
        with open(CLIENT_SECRET_FILE, "r", encoding="utf-8") as f:
            return json.load(f)

    print(f"'{CLIENT_SECRET_FILE}' not found. Enter the OAuth Desktop client values manually.")
    client_id = input("Client ID: ").strip()
    client_secret = input("Client secret: ").strip()
    return {
        "installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost"],
        }
    }


def main():
    config = build_client_config()
    flow = InstalledAppFlow.from_client_config(config, SCOPES)
    # access_type=offline + prompt=consent guarantees a refresh_token is returned.
    creds = flow.run_local_server(port=0, access_type="offline", prompt="consent")

    installed = config.get("installed") or config.get("web") or {}
    client_id = installed.get("client_id", "")
    client_secret = installed.get("client_secret", "")

    print("\n" + "=" * 70)
    print("SUCCESS. Add these as GitHub repository Secrets:")
    print("=" * 70)
    print(f"GDRIVE_CLIENT_ID     = {client_id}")
    print(f"GDRIVE_CLIENT_SECRET = {client_secret}")
    print(f"GDRIVE_REFRESH_TOKEN = {creds.refresh_token}")
    print("GDRIVE_FOLDER_ID     = <open your vault folder in Drive; copy the ID")
    print("                        from the URL .../folders/THIS_PART>")
    print("=" * 70)
    if not creds.refresh_token:
        print("\nWARNING: no refresh_token returned. Revoke the app's access at")
        print("https://myaccount.google.com/permissions and run this script again.")


if __name__ == "__main__":
    main()
