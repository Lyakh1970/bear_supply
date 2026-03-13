"""
Скрипт для первичной OAuth-авторизации.

Запустите один раз локально:
    python auth_drive.py

Откроется браузер для авторизации Google-аккаунта.
После этого будет создан token.json с refresh_token.
Скопируйте token.json на сервер.

Повторная авторизация нужна только если:
- Токен был отозван в Google Account → Security → Third-party apps
- Изменились scopes (области доступа)
"""

from google_auth_oauthlib.flow import InstalledAppFlow
import os

# Те же scopes, что и в google_auth.py
SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/spreadsheets",
]

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
CREDS_FILE = os.path.join(ROOT_DIR, "client_secret.json")
TOKEN_FILE = os.path.join(ROOT_DIR, "token.json")


def main():
    if not os.path.exists(CREDS_FILE):
        print(f"ERROR: {CREDS_FILE} not found!")
        print("Download it from Google Cloud Console → APIs & Services → Credentials")
        return
    
    print("Starting OAuth flow...")
    print("A browser window will open for authorization.")
    print()
    
    flow = InstalledAppFlow.from_client_secrets_file(CREDS_FILE, SCOPES)
    
    # access_type='offline' — критически важно для получения refresh_token
    creds = flow.run_local_server(
        port=0,
        access_type='offline',
        prompt='consent'  # Форсируем показ consent screen для получения refresh_token
    )
    
    with open(TOKEN_FILE, "w") as f:
        f.write(creds.to_json())
    
    print()
    print(f"✅ token.json created: {TOKEN_FILE}")
    print()
    print("Now copy this file to your server:")
    print(f"  scp {TOKEN_FILE} root@YOUR_SERVER:/opt/bear_supply/creds/token.json")
    print()
    print("Or copy the contents manually:")
    print("-" * 60)
    with open(TOKEN_FILE, "r") as f:
        print(f.read())
    print("-" * 60)


if __name__ == "__main__":
    main()
