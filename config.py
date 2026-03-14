import json
import os

def _get_env(name: str, default: str | None = None) -> str | None:
    val = os.getenv(name, default)
    if val is None or val == "":
        return None
    return val

# ─────────────────────────────────────────────────────────────────────────────
# Telegram
# ─────────────────────────────────────────────────────────────────────────────
TELEGRAM_TOKEN = _get_env("BEAR_SUPPLY_TOKEN") or _get_env("TELEGRAM_BOT_TOKEN")
if not TELEGRAM_TOKEN:
    raise RuntimeError("Env BEAR_SUPPLY_TOKEN or TELEGRAM_BOT_TOKEN is not set")

GROUP_ID = int(_get_env("BEAR_SUPPLY_GROUP_ID", "-5118688028"))

DOWNLOAD_DIR = _get_env("BEAR_SUPPLY_DOWNLOAD_DIR", "/opt/bear_supply/uploads")

# ─────────────────────────────────────────────────────────────────────────────
# PostgreSQL (Digital Ocean Managed Database) - PRIMARY STORAGE
# ─────────────────────────────────────────────────────────────────────────────
DATABASE_URL = _get_env("DATABASE_URL")

# ─────────────────────────────────────────────────────────────────────────────
# Nextcloud - FILE STORAGE
# ─────────────────────────────────────────────────────────────────────────────
NEXTCLOUD_BASE_URL = _get_env("NEXTCLOUD_BASE_URL")  # e.g. https://cloud.bearcloud.one
NEXTCLOUD_USERNAME = _get_env("NEXTCLOUD_USERNAME")  # e.g. bearbot
NEXTCLOUD_PASSWORD = _get_env("NEXTCLOUD_PASSWORD")  # App password (not regular password!)
NEXTCLOUD_BASE_FOLDER = _get_env("NEXTCLOUD_BASE_FOLDER", "Documents/BearBox Docs/Finance")
NEXTCLOUD_SHARE_PASSWORD = _get_env("NEXTCLOUD_SHARE_PASSWORD", "BearBox2026!")  # Password for public links

# ─────────────────────────────────────────────────────────────────────────────
# Google Sheets via Apps Script Web App - UI LAYER
# ─────────────────────────────────────────────────────────────────────────────
SHEETS_WEBAPP_URL = _get_env("SHEETS_WEBAPP_URL")  # Google Apps Script deployment URL

# ─────────────────────────────────────────────────────────────────────────────
# LEGACY: Google OAuth (deprecated, kept for reference)
# ─────────────────────────────────────────────────────────────────────────────
TOKEN_JSON = _get_env("BEAR_SUPPLY_TOKEN_JSON", "/opt/bear_supply/creds/token.json")
SHEET_ID = _get_env("BEAR_SUPPLY_SHEET_ID")
WORKSHEET_NAME = _get_env("BEAR_SUPPLY_WORKSHEET_NAME", "Purchases_Log")
DRIVE_FOLDER_ID = _get_env("BEAR_SUPPLY_DRIVE_FOLDER_ID", "")

# Маппинг "как в подписи" → "ключ из листа Suppliers" (чтобы в таблице работал поиск Platform).
# Пример: BEAR_SUPPLY_SUPPLIER_ALIASES='{"Amazon":"amazon.pl","Amazon ES":"amazon.es"}'
def _parse_supplier_aliases() -> dict[str, str] | None:
    raw = _get_env("BEAR_SUPPLY_SUPPLIER_ALIASES")
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None

SUPPLIER_ALIASES = _parse_supplier_aliases()

# Значения по умолчанию для Category и Project (если не указаны в подписи) — для Report_Key
DEFAULT_CATEGORY = _get_env("BEAR_SUPPLY_DEFAULT_CATEGORY")
DEFAULT_PROJECT = _get_env("BEAR_SUPPLY_DEFAULT_PROJECT")
