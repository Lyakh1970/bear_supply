from google_auth_oauthlib.flow import InstalledAppFlow
import pickle
import os

SCOPES = ["https://www.googleapis.com/auth/drive"]

# client_secret.json в корне проекта; на сервере можно задать через env
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CREDS_FILE = os.environ.get("CLIENT_SECRET_JSON", os.path.join(ROOT_DIR, "client_secret.json"))
TOKEN_FILE = os.environ.get("DRIVE_TOKEN_FILE", os.path.join(ROOT_DIR, "token.pickle"))


def authenticate():
    creds = None

    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "rb") as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file(CREDS_FILE, SCOPES)
        creds = flow.run_console()

        with open(TOKEN_FILE, "wb") as token:
            pickle.dump(creds, token)

    return creds


if __name__ == "__main__":
    creds = authenticate()
    print("Drive OAuth OK")
