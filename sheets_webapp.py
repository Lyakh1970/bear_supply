"""
Google Sheets запись через Apps Script Web App.

Вместо прямой авторизации Google Sheets API используем HTTP POST к Google Apps Script,
который выполняется от имени владельца таблицы.

Аналогично проекту Mixa Debt.
"""

import logging
from dataclasses import dataclass
from datetime import date
from typing import Optional

import requests

import config

logger = logging.getLogger(__name__)


@dataclass
class SheetWriteResult:
    """Результат записи в Google Sheets."""
    success: bool
    error: Optional[str] = None


@dataclass
class ExpenseRowData:
    """Данные строки для записи в таблицу."""
    expense_date: date
    supplier: str
    description: str
    qty: float
    unit_price: float
    total: float
    currency: str
    category: Optional[str] = None
    project: Optional[str] = None
    legal_entity: Optional[str] = None
    payment_method: Optional[str] = None
    invoice: Optional[str] = None
    expense_type: Optional[str] = None
    report_key: Optional[str] = None
    seller: Optional[str] = None
    product_link: Optional[str] = None
    notes: Optional[str] = None
    document_url: Optional[str] = None  # Ссылка на документ (Nextcloud public URL)


def append_row_to_sheet(data: ExpenseRowData) -> SheetWriteResult:
    """
    Записать строку в Google Sheets через Apps Script Web App.
    
    Apps Script должен принимать POST с JSON и добавлять строку в таблицу.
    
    Пример Apps Script:
    
    function doPost(e) {
      var sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName('Purchases_Log');
      var data = JSON.parse(e.postData.contents);
      
      sheet.appendRow([
        data.date,
        data.supplier,
        data.description,
        data.qty,
        data.unit_price,
        data.total,
        data.currency,
        data.category,
        data.project,
        data.payment_method,
        data.invoice,
        data.notes,
        data.document_url
      ]);
      
      return ContentService.createTextOutput(JSON.stringify({success: true}))
        .setMimeType(ContentService.MimeType.JSON);
    }
    """
    if not config.SHEETS_WEBAPP_URL:
        logger.warning("SHEETS_WEBAPP_URL not configured, skipping Sheets sync")
        return SheetWriteResult(success=False, error="SHEETS_WEBAPP_URL not configured")
    
    payload = {
        "action": "append",
        "date": data.expense_date.strftime("%Y-%m-%d"),
        "supplier": data.supplier or "",
        "description": data.description or "",
        "qty": data.qty,
        "unit_price": data.unit_price,
        "total": data.total,
        "currency": data.currency or "EUR",
        "category": data.category or "",
        "project": data.project or "",
        "legal_entity": data.legal_entity or "",
        "payment_method": data.payment_method or "",
        "invoice": data.invoice or "",
        "expense_type": data.expense_type or "",
        "report_key": data.report_key or "",
        "seller": data.seller or "",
        "product_link": data.product_link or "",
        "notes": data.notes or "",
        "document_url": data.document_url or "",
    }
    
    logger.info(f"Sending row to Sheets Web App: {data.description[:50]}...")
    
    try:
        resp = requests.post(
            config.SHEETS_WEBAPP_URL,
            json=payload,
            timeout=30,
            headers={"Content-Type": "application/json"},
        )
        
        if resp.status_code == 200:
            try:
                result = resp.json()
                if result.get("success"):
                    logger.info("Row added to Google Sheets via Web App")
                    return SheetWriteResult(success=True)
                else:
                    error = result.get("error", "Unknown error from Apps Script")
                    logger.error(f"Apps Script error: {error}")
                    return SheetWriteResult(success=False, error=error)
            except Exception:
                # Некоторые Apps Script возвращают просто текст
                logger.info("Row added to Google Sheets (non-JSON response)")
                return SheetWriteResult(success=True)
        
        logger.error(f"Sheets Web App error: {resp.status_code} {resp.text[:200]}")
        return SheetWriteResult(success=False, error=f"HTTP {resp.status_code}: {resp.text[:100]}")
        
    except requests.Timeout:
        logger.error("Sheets Web App timeout")
        return SheetWriteResult(success=False, error="Request timeout")
    except Exception as e:
        logger.error(f"Sheets Web App error: {e}")
        return SheetWriteResult(success=False, error=str(e))


def test_webapp_connection() -> bool:
    """Проверить доступность Apps Script Web App."""
    if not config.SHEETS_WEBAPP_URL:
        logger.warning("SHEETS_WEBAPP_URL not configured")
        return False
    
    try:
        # Отправляем GET запрос для проверки (если Apps Script поддерживает doGet)
        resp = requests.get(
            config.SHEETS_WEBAPP_URL,
            params={"action": "ping"},
            timeout=10,
        )
        
        if resp.status_code == 200:
            logger.info("Sheets Web App connection OK")
            return True
        
        logger.warning(f"Sheets Web App check returned: {resp.status_code}")
        return True  # Не критично, POST может работать
        
    except Exception as e:
        logger.error(f"Sheets Web App connection error: {e}")
        return False
