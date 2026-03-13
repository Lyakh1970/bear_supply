"""
Модуль для работы с PostgreSQL (Digital Ocean Managed Database).
Таблицы: expense_entries, documents, suppliers, categories, projects, payment_methods, currencies.
"""

import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import date, datetime
from dataclasses import dataclass
from typing import Optional
from contextlib import contextmanager

import config


@contextmanager
def get_connection():
    """Контекстный менеджер для подключения к БД."""
    if not config.DATABASE_URL:
        raise RuntimeError("DATABASE_URL is not set in environment")
    conn = psycopg2.connect(config.DATABASE_URL)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ─────────────────────────────────────────────────────────────────────────────
# Справочники: получение списков для выбора в диалоге
# ─────────────────────────────────────────────────────────────────────────────

def get_suppliers() -> list[dict]:
    """Список поставщиков для inline keyboard."""
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT id, name, supplier_type, country_code FROM suppliers ORDER BY name")
            return [dict(row) for row in cur.fetchall()]


def get_categories() -> list[dict]:
    """Список категорий."""
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT id, name FROM categories ORDER BY name")
            return [dict(row) for row in cur.fetchall()]


def get_projects() -> list[dict]:
    """Список проектов (vessels)."""
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT id, name FROM projects ORDER BY name")
            return [dict(row) for row in cur.fetchall()]


def get_payment_methods() -> list[dict]:
    """Список способов оплаты."""
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT id, name FROM payment_methods ORDER BY name")
            return [dict(row) for row in cur.fetchall()]


def get_currencies() -> list[dict]:
    """Список валют."""
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT code, name FROM currencies ORDER BY code")
            return [dict(row) for row in cur.fetchall()]


# ─────────────────────────────────────────────────────────────────────────────
# Поиск по справочникам
# ─────────────────────────────────────────────────────────────────────────────

def find_supplier_by_name(name: str) -> Optional[dict]:
    """Найти поставщика по имени (case-insensitive)."""
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT id, name, supplier_type, country_code FROM suppliers WHERE LOWER(name) = LOWER(%s)",
                (name.strip(),)
            )
            row = cur.fetchone()
            return dict(row) if row else None


def find_category_by_name(name: str) -> Optional[dict]:
    """Найти категорию по имени."""
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT id, name FROM categories WHERE LOWER(name) = LOWER(%s)",
                (name.strip(),)
            )
            row = cur.fetchone()
            return dict(row) if row else None


def find_project_by_name(name: str) -> Optional[dict]:
    """Найти проект по имени."""
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT id, name FROM projects WHERE LOWER(name) = LOWER(%s)",
                (name.strip(),)
            )
            row = cur.fetchone()
            return dict(row) if row else None


def find_payment_method_by_name(name: str) -> Optional[dict]:
    """Найти способ оплаты по имени."""
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT id, name FROM payment_methods WHERE LOWER(name) = LOWER(%s)",
                (name.strip(),)
            )
            row = cur.fetchone()
            return dict(row) if row else None


# ─────────────────────────────────────────────────────────────────────────────
# Вставка документа
# ─────────────────────────────────────────────────────────────────────────────

def insert_document(
    telegram_file_id: Optional[str] = None,
    telegram_message_id: Optional[int] = None,
    telegram_chat_id: Optional[int] = None,
    original_filename: Optional[str] = None,
    mime_type: Optional[str] = None,
    file_size_bytes: Optional[int] = None,
    drive_url: Optional[str] = None,
    caption_raw: Optional[str] = None,
    ocr_text_raw: Optional[str] = None,
) -> int:
    """Вставить запись о документе, вернуть document_id."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO documents (
                    telegram_file_id,
                    telegram_message_id,
                    telegram_chat_id,
                    original_filename,
                    mime_type,
                    file_size_bytes,
                    drive_url,
                    caption_raw,
                    ocr_text_raw
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                telegram_file_id,
                telegram_message_id,
                telegram_chat_id,
                original_filename,
                mime_type,
                file_size_bytes,
                drive_url,
                caption_raw,
                ocr_text_raw,
            ))
            return cur.fetchone()[0]


# ─────────────────────────────────────────────────────────────────────────────
# Вставка записи расхода
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ExpenseEntryData:
    """Данные для вставки в expense_entries."""
    expense_date: date
    description: str
    qty: float = 1.0
    unit_price: Optional[float] = None
    total: Optional[float] = None
    currency_code: Optional[str] = None
    supplier_id: Optional[int] = None
    supplier_name_raw: Optional[str] = None
    category_id: Optional[int] = None
    project_id: Optional[int] = None
    payment_method_id: Optional[int] = None
    invoice: Optional[str] = None
    expense_type: Optional[str] = None
    report_key: Optional[str] = None
    notes: Optional[str] = None
    document_id: Optional[int] = None
    parse_source: Optional[str] = None
    parse_status: str = "draft"
    parse_confidence: Optional[float] = None


def insert_expense_entry(data: ExpenseEntryData) -> int:
    """Вставить запись расхода, вернуть entry_id."""
    month_key = data.expense_date.strftime("%Y-%m")
    
    # Если total не указан, вычисляем
    total = data.total
    if total is None and data.unit_price is not None:
        total = data.unit_price * data.qty
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO expense_entries (
                    expense_date,
                    month_key,
                    supplier_id,
                    supplier_name_raw,
                    description,
                    qty,
                    unit_price,
                    total,
                    currency_code,
                    category_id,
                    project_id,
                    payment_method_id,
                    invoice,
                    expense_type,
                    report_key,
                    notes,
                    document_id,
                    parse_source,
                    parse_status,
                    parse_confidence
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
                RETURNING id
            """, (
                data.expense_date,
                month_key,
                data.supplier_id,
                data.supplier_name_raw,
                data.description,
                data.qty,
                data.unit_price,
                total,
                data.currency_code,
                data.category_id,
                data.project_id,
                data.payment_method_id,
                data.invoice,
                data.expense_type,
                data.report_key,
                data.notes,
                data.document_id,
                data.parse_source,
                data.parse_status,
                data.parse_confidence,
            ))
            return cur.fetchone()[0]


# ─────────────────────────────────────────────────────────────────────────────
# Вспомогательные функции
# ─────────────────────────────────────────────────────────────────────────────

def create_supplier_if_not_exists(name: str, supplier_type: Optional[str] = None, country_code: Optional[str] = None) -> int:
    """Создать поставщика, если не существует. Вернуть supplier_id."""
    existing = find_supplier_by_name(name)
    if existing:
        return existing["id"]
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO suppliers (name, supplier_type, country_code)
                VALUES (%s, %s, %s)
                ON CONFLICT (name) DO UPDATE SET name = EXCLUDED.name
                RETURNING id
            """, (name.strip(), supplier_type, country_code))
            return cur.fetchone()[0]


def test_connection() -> bool:
    """Проверить подключение к БД."""
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                return True
    except Exception as e:
        print(f"DB connection error: {e}")
        return False
