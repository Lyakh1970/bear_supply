import gspread
from datetime import datetime

from google_auth import load_credentials

# Возможные варианты заголовков (на случай разного регистра/формата)
HEADER_ALIASES = {
    "date": {"date", "дата"},
    "supplier": {"supplier", "продавец", "поставщик"},
    "description": {"description", "описание", "item", "товар"},
    "qty": {"qty", "quantity", "кол-во", "количество"},
    "unit_price": {"unit price", "unit_price", "price", "цена", "unitprice"},
    "currency": {"currency", "валюта"},
    "category": {"category", "категория"},
    "project": {"project", "проект"},
    "document_link": {"document_link", "document link", "link", "ссылка", "doc_link"},
}

def _norm(s: str) -> str:
    return " ".join(s.strip().lower().replace("_", " ").split())

def _build_header_map(headers: list[str]) -> dict[str, int]:
    norm_headers = [_norm(h) for h in headers]
    idx_map: dict[str, int] = {}
    for key, aliases in HEADER_ALIASES.items():
        for i, h in enumerate(norm_headers):
            if h in aliases:
                idx_map[key] = i
                break
    return idx_map

def append_purchase(
    token_json_path: str,
    sheet_id: str,
    worksheet_name: str,
    supplier: str,
    description: str,
    qty: float,
    unit_price: float,
    currency: str,
    document_link: str,
    category: str | None = None,
    project: str | None = None,
):
    creds = load_credentials(token_json_path)
    client = gspread.authorize(creds)

    ws = client.open_by_key(sheet_id).worksheet(worksheet_name)

    headers = ws.row_values(1)
    if not headers:
        raise RuntimeError("Worksheet header row (row 1) is empty")

    hm = _build_header_map(headers)

    required = ["date", "supplier", "description", "qty", "unit_price", "currency", "document_link"]
    missing = [k for k in required if k not in hm]
    if missing:
        raise RuntimeError(
            f"Missing required columns in sheet header: {missing}. "
            f"Headers found: {headers}"
        )

    row = [""] * len(headers)
    today = datetime.now().strftime("%Y-%m-%d")

    row[hm["date"]] = today
    row[hm["supplier"]] = supplier
    row[hm["description"]] = description
    row[hm["qty"]] = qty
    row[hm["unit_price"]] = unit_price
    row[hm["currency"]] = currency
    row[hm["document_link"]] = document_link
    if "category" in hm and category:
        row[hm["category"]] = category
    if "project" in hm and project:
        row[hm["project"]] = project

    ws.append_row(row, value_input_option="USER_ENTERED")