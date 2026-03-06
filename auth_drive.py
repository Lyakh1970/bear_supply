from google_auth_oauthlib.flow import InstalledAppFlow
import os

SCOPES = ["https://www.googleapis.com/auth/drive"]

# Файлы в корне проекта (где лежит client_secret.json)
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
CREDS_FILE = os.path.join(ROOT_DIR, "client_secret.json")
TOKEN_FILE = os.path.join(ROOT_DIR, "token.json")

flow = InstalledAppFlow.from_client_secrets_file(CREDS_FILE, SCOPES)

creds = flow.run_local_server(port=0)

with open(TOKEN_FILE, "w") as f:
    f.write(creds.to_json())

print("token.json created")
