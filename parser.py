import re
from dataclasses import dataclass

@dataclass
class ParsedPurchase:
    supplier: str
    description: str
    qty: float
    price: float
    currency: str

def _parse_price_and_currency(raw: str) -> tuple[float, str]:
    s = raw.strip()
    currency = "EUR"
    if "€" in s or "eur" in s.lower():
        currency = "EUR"
    if "$" in s or "usd" in s.lower():
        currency = "USD"

    s = s.replace("€", "").replace("$", "")
    s = re.sub(r"\b(EUR|USD)\b", "", s, flags=re.IGNORECASE).strip()
    s = s.replace(",", ".")
    m = re.search(r"(-?\d+(?:\.\d+)?)", s)
    if not m:
        raise ValueError(f"Cannot parse price from: {raw}")
    return float(m.group(1)), currency

def _parse_qty(raw: str) -> float:
    s = raw.strip().lower().replace(",", ".")
    m = re.search(r"(\d+(?:\.\d+)?)", s)
    if not m:
        raise ValueError(f"Cannot parse qty from: {raw}")
    return float(m.group(1))

def parse_caption(caption: str) -> ParsedPurchase:
    """
    Форматы:
    1) Supplier; Description; 120€
    2) Supplier; Description; Qty; 120€
    """
    if not caption:
        raise ValueError("Empty caption")

    parts = [p.strip() for p in caption.split(";") if p.strip()]
    if len(parts) == 3:
        supplier, description, price_raw = parts
        qty = 1.0
    elif len(parts) == 4:
        supplier, description, qty_raw, price_raw = parts
        qty = _parse_qty(qty_raw)
    else:
        raise ValueError("Caption format must be 'Supplier; Description; Price' or 'Supplier; Description; Qty; Price'")

    price, currency = _parse_price_and_currency(price_raw)

    if not supplier or not description:
        raise ValueError("Supplier/Description is empty")

    return ParsedPurchase(
        supplier=supplier,
        description=description,
        qty=qty,
        price=price,
        currency=currency
    )
