"""
Google API авторизация через Service Account.

Service Account не требует интерактивной авторизации и идеально подходит для серверных приложений.
Просто скачайте JSON-ключ из Google Cloud Console и укажите путь в GOOGLE_SERVICE_ACCOUNT_FILE.
"""

import os
from google.oauth2.service_account import Credentials

# Required scopes
SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/spreadsheets",
]


def load_credentials(service_account_file: str) -> Credentials:
    """
    Загрузить credentials из Service Account JSON файла.
    
    Args:
        service_account_file: Путь к JSON-файлу Service Account
        
    Returns:
        Credentials для Google API
    """
    if not os.path.exists(service_account_file):
        raise FileNotFoundError(
            f"Service Account file not found: {service_account_file}\n"
            f"Download it from Google Cloud Console → IAM → Service Accounts"
        )
    
    creds = Credentials.from_service_account_file(
        service_account_file,
        scopes=SCOPES
    )
    
    return creds


def get_service_account_email(service_account_file: str) -> str:
    """Получить email Service Account (для sharing Google Drive/Sheets)."""
    import json
    with open(service_account_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("client_email", "")
