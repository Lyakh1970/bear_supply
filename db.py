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


def get_legal_entities() -> list[dict]:
    """Список компаний (legal entities) для выбора в диалоге."""
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT id, code, name FROM legal_entities ORDER BY id")
            return [dict(row) for row in cur.fetchall()]


def find_legal_entity_by_code(code: str) -> Optional[dict]:
    """Найти компанию по коду."""
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT id, code, name FROM legal_entities WHERE code = %s",
                (code.strip(),)
            )
            row = cur.fetchone()
            return dict(row) if row else None


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
# Вставка и обновление документов
# ─────────────────────────────────────────────────────────────────────────────

def insert_document(
    telegram_file_id: Optional[str] = None,
    telegram_message_id: Optional[int] = None,
    telegram_chat_id: Optional[int] = None,
    original_filename: Optional[str] = None,
    mime_type: Optional[str] = None,
    file_size_bytes: Optional[int] = None,
    caption_raw: Optional[str] = None,
    ocr_text_raw: Optional[str] = None,
    # New storage fields
    storage_backend: Optional[str] = None,
    storage_path: Optional[str] = None,
    public_url: Optional[str] = None,
    share_password: Optional[str] = None,
    upload_status: str = "pending",
    upload_error: Optional[str] = None,
    # Legacy field (deprecated)
    drive_url: Optional[str] = None,
) -> int:
    """
    Вставить запись о документе, вернуть document_id.
    
    New fields:
        storage_backend: 'nextcloud' | 'gdrive' (legacy)
        storage_path: internal path in storage
        public_url: public link to document
        share_password: password for public link (if enforced by server policy)
        upload_status: 'pending' | 'uploaded' | 'failed'
        upload_error: error message if failed
    """
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
                    caption_raw,
                    ocr_text_raw,
                    storage_backend,
                    storage_path,
                    public_url,
                    share_password,
                    upload_status,
                    upload_error,
                    drive_url
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                telegram_file_id,
                telegram_message_id,
                telegram_chat_id,
                original_filename,
                mime_type,
                file_size_bytes,
                caption_raw,
                ocr_text_raw,
                storage_backend,
                storage_path,
                public_url,
                share_password,
                upload_status,
                upload_error,
                drive_url,
            ))
            return cur.fetchone()[0]


def update_document_upload_status(
    document_id: int,
    storage_backend: str,
    storage_path: Optional[str] = None,
    public_url: Optional[str] = None,
    upload_status: str = "uploaded",
    upload_error: Optional[str] = None,
) -> None:
    """
    Обновить статус загрузки документа после upload в storage.
    
    Вызывается после успешной/неуспешной загрузки в Nextcloud.
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE documents SET
                    storage_backend = %s,
                    storage_path = %s,
                    public_url = %s,
                    upload_status = %s,
                    upload_error = %s
                WHERE id = %s
            """, (
                storage_backend,
                storage_path,
                public_url,
                upload_status,
                upload_error,
                document_id,
            ))


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
    legal_entity_id: Optional[int] = None
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
                    legal_entity_id,
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
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
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
                data.legal_entity_id,
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
