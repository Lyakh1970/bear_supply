#!/usr/bin/env python3
"""
Тестовый скрипт доступа к Google Sheets и Google Drive.
Использует сервисный аккаунт (google-sa.json).

Переменная окружения GOOGLE_APPLICATION_CREDENTIALS — путь к JSON-ключу.
По умолчанию на сервере DO: /opt/bear_supply/creds/google-sa.json
"""

import os
import sys

# Путь к ключу: из переменной окружения или значение по умолчанию для DO
DEFAULT_CREDS_PATH = "/opt/bear_supply/creds/google-sa.json"
CREDS_PATH = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", DEFAULT_CREDS_PATH)

SHEET_ID = "1m6zvvp1CNaPknA7Y6FuIrLksm9b0cC4rU-R54H9LMug"
DRIVE_FOLDER_ID = "1PNcDcQf09J4SlepPPUBNTaMnfEmmdOb2"


def test_sheets():
    """Проверка доступа к таблице BEAR_SUPPLY_2026."""
    import gspread
    from google.oauth2.service_account import Credentials

    if not os.path.isfile(CREDS_PATH):
        print(f"Файл ключа не найден: {CREDS_PATH}")
        print("Задайте GOOGLE_APPLICATION_CREDENTIALS или положите google-sa.json в нужное место.")
        return False

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = Credentials.from_service_account_file(CREDS_PATH, scopes=scopes)
    client = gspread.authorize(creds)

    try:
        sh = client.open_by_key(SHEET_ID)
        print(f"[Sheets] Таблица: «{sh.title}»")
        sheet = sh.sheet1
        print(f"        Первый лист: «{sheet.title}»")
        row1 = sheet.row_values(1)
        if row1:
            print(f"        Первая строка: {row1}")
        else:
            print("        Первая строка пуста.")
        return True
    except Exception as e:
        print(f"[Sheets] Ошибка: {e}")
        print("        Убедитесь, что таблице открыт доступ для сервисного аккаунта (почта бота).")
        return False


def test_drive():
    """Проверка доступа к папке BEAR_SUPPLY на Google Drive."""
    from google.oauth2.service_account import Credentials
    from googleapiclient.discovery import build

    if not os.path.isfile(CREDS_PATH):
        print(f"Файл ключа не найден: {CREDS_PATH}")
        return False

    scopes = ["https://www.googleapis.com/auth/drive.readonly"]
    creds = Credentials.from_service_account_file(CREDS_PATH, scopes=scopes)
    service = build("drive", "v3", credentials=creds)

    try:
        folder = service.files().get(
            fileId=DRIVE_FOLDER_ID,
            fields="name, id, mimeType",
        ).execute()
        print(f"[Drive] Папка: «{folder.get('name')}» (id: {folder.get('id')})")
        # Список первых 5 элементов в папке
        results = (
            service.files()
            .list(
                q=f"'{DRIVE_FOLDER_ID}' in parents",
                pageSize=5,
                fields="files(name, id, mimeType)",
            )
            .execute()
        )
        files = results.get("files", [])
        if files:
            print("        Содержимое (до 5):")
            for f in files:
                print(f"          - {f.get('name')} ({f.get('mimeType')})")
        else:
            print("        Папка пуста.")
        return True
    except Exception as e:
        print(f"[Drive] Ошибка: {e}")
        print("        Убедитесь, что папке открыт доступ для сервисного аккаунта (почта бота).")
        return False


def main():
    print("Ключ:", CREDS_PATH)
    print()
    ok_sheets = test_sheets()
    print()
    ok_drive = test_drive()
    print()
    if ok_sheets and ok_drive:
        print("OK: Sheets и Drive доступны.")
        sys.exit(0)
    sys.exit(1)


if __name__ == "__main__":
    main()
