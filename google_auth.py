import json
import os
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

# Required scopes
SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/spreadsheets",
]

def load_credentials(token_json_path: str) -> Credentials:
    if not os.path.exists(token_json_path):
        raise FileNotFoundError(f"token.json not found: {token_json_path}")

    with open(token_json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    creds = Credentials.from_authorized_user_info(data, scopes=SCOPES)

    # refresh if needed
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        # persist updated token
        with open(token_json_path, "w", encoding="utf-8") as f:
            f.write(creds.to_json())

    return creds