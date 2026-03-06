import os

def _get_env(name: str, default: str | None = None) -> str | None:
    val = os.getenv(name, default)
    if val is None or val == "":
        return None
    return val

# Токен бота: BEAR_SUPPLY_TOKEN или TELEGRAM_BOT_TOKEN (для совместимости с .env)
TELEGRAM_TOKEN = _get_env("BEAR_SUPPLY_TOKEN") or _get_env("TELEGRAM_BOT_TOKEN")
if not TELEGRAM_TOKEN:
    raise RuntimeError("Env BEAR_SUPPLY_TOKEN or TELEGRAM_BOT_TOKEN is not set")

GROUP_ID = int(_get_env("BEAR_SUPPLY_GROUP_ID", "-5118688028"))

DOWNLOAD_DIR = _get_env("BEAR_SUPPLY_DOWNLOAD_DIR", "/opt/bear_supply/uploads")
TOKEN_JSON = _get_env("BEAR_SUPPLY_TOKEN_JSON", "/opt/bear_supply/creds/token.json")

SHEET_ID = _get_env("BEAR_SUPPLY_SHEET_ID")
if not SHEET_ID:
    raise RuntimeError("Env BEAR_SUPPLY_SHEET_ID is not set (use Google Sheet ID from URL)")

WORKSHEET_NAME = _get_env("BEAR_SUPPLY_WORKSHEET_NAME", "Purchases_Log")

# Optional: if empty/None -> upload to Drive root
DRIVE_FOLDER_ID = _get_env("BEAR_SUPPLY_DRIVE_FOLDER_ID", "")
