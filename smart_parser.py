"""
Умный парсер для извлечения данных из произвольной строки-подписи.

Примеры входных строк:
- "SAMSUNG EVO980, 150 EUR, 2 шт, Amazon PL"
- "12/03/2026 SAMSUNG EVO 980, 150 EUR, Amazon ES"
- "Amazon PL, 2x SSD Samsung 980 EVO, 300 EUR"
- "150€ Samsung SSD"
"""

import re
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional


@dataclass
class ParsedData:
    """Результат парсинга подписи."""
    description: Optional[str] = None
    unit_price: Optional[float] = None
    currency: Optional[str] = None
    qty: float = 1.0
    expense_date: Optional[date] = None
    supplier: Optional[str] = None
    supplier_raw: Optional[str] = None
    category: Optional[str] = None
    project: Optional[str] = None
    notes: Optional[str] = None
    confidence: float = 0.0
    missing_fields: list[str] = field(default_factory=list)
    parse_source: str = "caption"


# Известные поставщики для распознавания (нормализованное имя → варианты написания)
KNOWN_SUPPLIERS = {
    "amazon.es": ["amazon es", "amazon.es", "амазон es"],
    "amazon.pl": ["amazon pl", "amazon.pl", "амазон pl", "amazon"],
    "allegro.pl": ["allegro", "allegro.pl", "аллегро"],
    "aliexpress": ["aliexpress", "али", "алиэкспресс"],
    "temu": ["temu", "тему"],
    "pccomponente": ["pccomponente", "pc componentes", "pccomponentes"],
    "sugraher": ["sugraher"],
    "canaryonline": ["canaryonline", "canary online"],
    "digitalocean": ["digitalocean", "digital ocean", "do"],
    "zerotier": ["zerotier", "zero tier"],
    "openai": ["openai", "open ai"],
    "microsoft": ["microsoft", "ms"],
    "vesselfinder": ["vesselfinder", "vessel finder"],
    "maritime optima": ["maritime optima"],
}

# Валюты: символ/код → нормализованный код
CURRENCY_PATTERNS = {
    "EUR": [r"€", r"\beur\b", r"\bевро\b"],
    "USD": [r"\$", r"\busd\b", r"\bдолл", r"\bбакс"],
    "PLN": [r"\bzł\b", r"\bzl\b", r"\bpln\b", r"\bзлот"],
    "RUR": [r"₽", r"\brub\b", r"\brur\b", r"\bруб"],
}

# Паттерны для количества
QTY_PATTERNS = [
    r"(\d+(?:[.,]\d+)?)\s*(?:шт|pcs|pieces|штук|units?)",
    r"(\d+(?:[.,]\d+)?)\s*[xх]\s*",
    r"[xх]\s*(\d+(?:[.,]\d+)?)",
    r"(\d+(?:[.,]\d+)?)\s*(?:шт\.?|pcs\.?)",
]

# Паттерны для даты
DATE_PATTERNS = [
    (r"(\d{1,2})[/.](\d{1,2})[/.](\d{4})", "dmy"),
    (r"(\d{4})[-/](\d{1,2})[-/](\d{1,2})", "ymd"),
    (r"(\d{1,2})[-/](\d{1,2})[-/](\d{2})", "dmy_short"),
]


def _normalize(text: str) -> str:
    """Нормализовать текст для сравнения."""
    return " ".join(text.lower().strip().split())


def _extract_date(text: str) -> tuple[Optional[date], str]:
    """Извлечь дату из текста. Возвращает (дата, текст без даты)."""
    for pattern, fmt in DATE_PATTERNS:
        match = re.search(pattern, text)
        if match:
            try:
                if fmt == "dmy":
                    d, m, y = int(match.group(1)), int(match.group(2)), int(match.group(3))
                elif fmt == "ymd":
                    y, m, d = int(match.group(1)), int(match.group(2)), int(match.group(3))
                elif fmt == "dmy_short":
                    d, m, y = int(match.group(1)), int(match.group(2)), 2000 + int(match.group(3))
                else:
                    continue
                
                parsed_date = date(y, m, d)
                remaining = text[:match.start()] + text[match.end():]
                return parsed_date, remaining.strip()
            except ValueError:
                continue
    return None, text


def _extract_price_and_currency(text: str) -> tuple[Optional[float], Optional[str], str]:
    """Извлечь цену и валюту. Возвращает (цена, валюта, текст без цены)."""
    currency = None
    remaining = text
    
    # Сначала ищем валюту
    for curr_code, patterns in CURRENCY_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                currency = curr_code
                remaining = re.sub(pattern, " ", remaining, flags=re.IGNORECASE)
                break
        if currency:
            break
    
    # Ищем число (цену)
    price_match = re.search(r"(\d+(?:[.,]\d{1,2})?)", remaining)
    if price_match:
        price_str = price_match.group(1).replace(",", ".")
        price = float(price_str)
        remaining = remaining[:price_match.start()] + remaining[price_match.end():]
        return price, currency, remaining.strip()
    
    return None, currency, text


def _extract_qty(text: str) -> tuple[float, str]:
    """Извлечь количество. Возвращает (qty, текст без qty)."""
    for pattern in QTY_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            qty_str = match.group(1).replace(",", ".")
            qty = float(qty_str)
            remaining = text[:match.start()] + text[match.end():]
            return qty, remaining.strip()
    return 1.0, text


def _extract_supplier(text: str, suppliers_from_db: Optional[list[str]] = None) -> tuple[Optional[str], Optional[str], str]:
    """
    Извлечь поставщика.
    Возвращает (нормализованное имя, сырое имя, текст без поставщика).
    """
    text_lower = _normalize(text)
    
    # Сначала проверяем известных поставщиков
    for normalized_name, aliases in KNOWN_SUPPLIERS.items():
        for alias in aliases:
            if alias in text_lower:
                # Найти оригинальный текст для удаления
                idx = text_lower.find(alias)
                original_len = len(alias)
                supplier_raw = text[idx:idx + original_len]
                remaining = text[:idx] + text[idx + original_len:]
                return normalized_name, supplier_raw.strip(), remaining.strip()
    
    # Проверяем поставщиков из БД
    if suppliers_from_db:
        for supplier in suppliers_from_db:
            supplier_lower = supplier.lower()
            if supplier_lower in text_lower:
                idx = text_lower.find(supplier_lower)
                remaining = text[:idx] + text[idx + len(supplier):]
                return supplier, supplier, remaining.strip()
    
    return None, None, text


def _clean_description(text: str) -> str:
    """Очистить описание от лишних символов."""
    # Убираем разделители в начале и конце
    text = re.sub(r"^[\s,;.\-–—]+", "", text)
    text = re.sub(r"[\s,;.\-–—]+$", "", text)
    # Заменяем множественные пробелы
    text = " ".join(text.split())
    return text


def parse_caption(
    caption: str,
    suppliers_from_db: Optional[list[str]] = None,
    default_date: Optional[date] = None,
) -> ParsedData:
    """
    Парсит подпись и извлекает структурированные данные.
    
    Args:
        caption: Текст подписи к документу
        suppliers_from_db: Список имён поставщиков из БД для распознавания
        default_date: Дата по умолчанию (если None, используется сегодня)
    
    Returns:
        ParsedData с извлечёнными полями
    """
    if not caption or not caption.strip():
        return ParsedData(
            confidence=0.0,
            missing_fields=["description", "unit_price", "currency", "supplier"],
        )
    
    result = ParsedData()
    remaining = caption.strip()
    fields_found = 0
    
    # 1. Извлекаем дату
    expense_date, remaining = _extract_date(remaining)
    if expense_date:
        result.expense_date = expense_date
        fields_found += 1
    else:
        result.expense_date = default_date or date.today()
    
    # 2. Извлекаем поставщика
    supplier, supplier_raw, remaining = _extract_supplier(remaining, suppliers_from_db)
    if supplier:
        result.supplier = supplier
        result.supplier_raw = supplier_raw
        fields_found += 1
    
    # 3. Извлекаем количество
    qty, remaining = _extract_qty(remaining)
    result.qty = qty
    if qty != 1.0:
        fields_found += 1
    
    # 4. Извлекаем цену и валюту
    price, currency, remaining = _extract_price_and_currency(remaining)
    if price is not None:
        result.unit_price = price
        fields_found += 1
    if currency:
        result.currency = currency
        fields_found += 1
    
    # 5. Остаток — это описание
    description = _clean_description(remaining)
    if description:
        result.description = description
        fields_found += 1
    
    # 6. Вычисляем confidence и missing_fields
    missing = []
    if not result.description:
        missing.append("description")
    if result.unit_price is None:
        missing.append("unit_price")
    if not result.currency:
        missing.append("currency")
    if not result.supplier:
        missing.append("supplier")
    
    result.missing_fields = missing
    
    # Confidence: базово 0.5, +0.1 за каждое найденное поле, -0.15 за каждое критическое пропущенное
    confidence = 0.5 + (fields_found * 0.1)
    if not result.description:
        confidence -= 0.2
    if result.unit_price is None:
        confidence -= 0.15
    result.confidence = max(0.0, min(1.0, confidence))
    
    return result


def is_parse_sufficient(parsed: ParsedData) -> bool:
    """Проверить, достаточно ли данных для сохранения без диалога."""
    return (
        parsed.description is not None
        and parsed.unit_price is not None
        and parsed.confidence >= 0.6
    )


def format_preview(parsed: ParsedData) -> str:
    """Форматировать превью для отправки пользователю."""
    lines = []
    
    if parsed.expense_date:
        lines.append(f"📅 Дата: {parsed.expense_date.strftime('%d.%m.%Y')}")
    if parsed.description:
        lines.append(f"📦 Описание: {parsed.description}")
    if parsed.qty != 1.0:
        lines.append(f"🔢 Кол-во: {parsed.qty}")
    if parsed.unit_price is not None:
        price_str = f"{parsed.unit_price:.2f}"
        if parsed.currency:
            price_str += f" {parsed.currency}"
        lines.append(f"💰 Цена: {price_str}")
    if parsed.supplier:
        lines.append(f"🏪 Поставщик: {parsed.supplier}")
    
    if parsed.missing_fields:
        lines.append("")
        lines.append(f"❓ Не указано: {', '.join(parsed.missing_fields)}")
    
    return "\n".join(lines)
