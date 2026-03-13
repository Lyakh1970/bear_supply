"""
Google API авторизация через OAuth 2.0 с автоматическим refresh token.

После первичной авторизации токен автоматически обновляется без ручного вмешательства.
Требуется только один раз пройти авторизацию через auth_drive.py.
"""

import json
import os
import logging
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

logger = logging.getLogger(__name__)

# Required scopes - и Drive, и Sheets
SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/spreadsheets",
]


def load_credentials(token_json_path: str) -> Credentials:
    """
    Загрузить credentials из token.json с автоматическим refresh.
    
    Если токен истёк — автоматически обновляется через refresh_token.
    Обновлённый токен сохраняется обратно в файл.
    """
    if not os.path.exists(token_json_path):
        raise FileNotFoundError(
            f"token.json not found: {token_json_path}\n"
            f"Run auth_drive.py to create it."
        )

    with open(token_json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    creds = Credentials.from_authorized_user_info(data, scopes=SCOPES)

    # Автоматический refresh если токен истёк
    if creds.expired and creds.refresh_token:
        logger.info("Token expired, refreshing...")
        try:
            creds.refresh(Request())
            # Сохраняем обновлённый токен
            with open(token_json_path, "w", encoding="utf-8") as f:
                f.write(creds.to_json())
            logger.info("Token refreshed and saved")
        except Exception as e:
            logger.error(f"Failed to refresh token: {e}")
            raise RuntimeError(
                f"Token refresh failed: {e}\n"
                f"You may need to re-run auth_drive.py"
            ) from e

    return creds
