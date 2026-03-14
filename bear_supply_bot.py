import os
import logging
from pathlib import Path
from datetime import date
from dataclasses import dataclass

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    filters,
    ContextTypes,
)

import config
from smart_parser import parse_caption, is_parse_sufficient, format_preview, ParsedData
from nextcloud_storage import upload_file_to_nextcloud, UploadResult
from sheets_webapp import append_row_to_sheet, ExpenseRowData
import db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)
logger = logging.getLogger(__name__)

Path(config.DOWNLOAD_DIR).mkdir(parents=True, exist_ok=True)

# Глобальный флаг доступности PostgreSQL (проверяется при старте)
DB_AVAILABLE = False

# Состояния для ConversationHandler (диалоговый режим)
(
    STATE_DESCRIPTION,
    STATE_DATE,
    STATE_PRICE,
    STATE_CURRENCY,
    STATE_QTY,
    STATE_SUPPLIER,
    STATE_NEW_SUPPLIER,
    STATE_CATEGORY,
    STATE_PROJECT,
    STATE_PAYMENT,
    STATE_NOTES,
    STATE_CONFIRM,
) = range(12)

# Callback data prefixes
CB_SAVE = "save"
CB_SAVE_DRAFT = "save_draft"
CB_EDIT = "edit"
CB_CANCEL = "cancel"
CB_SHORT_FORM = "short_form"
CB_FULL_FORM = "full_form"
CB_SKIP = "skip"
CB_NEW_SUPPLIER = "new_supplier"
CB_DATE_TODAY = "date_today"


def _get_confirm_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура: Сохранить / Исправить / Отмена."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Сохранить", callback_data=CB_SAVE),
            InlineKeyboardButton("✏️ Исправить", callback_data=CB_EDIT),
        ],
        [InlineKeyboardButton("❌ Отмена", callback_data=CB_CANCEL)],
    ])


def _get_partial_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для частичного парсинга."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("💾 Сохранить черновик", callback_data=CB_SAVE_DRAFT),
            InlineKeyboardButton("✏️ Дополнить", callback_data=CB_EDIT),
        ],
        [InlineKeyboardButton("❌ Отмена", callback_data=CB_CANCEL)],
    ])


def _get_no_caption_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура: нет подписи."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📝 Короткая форма", callback_data=CB_SHORT_FORM),
            InlineKeyboardButton("📋 Полная форма", callback_data=CB_FULL_FORM),
        ],
        [InlineKeyboardButton("❌ Отмена", callback_data=CB_CANCEL)],
    ])


def _get_date_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора даты."""
    today = date.today().strftime("%d.%m.%Y")
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"📅 Сегодня ({today})", callback_data=CB_DATE_TODAY)],
    ])


def _get_currency_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора валюты."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("EUR", callback_data="cur_EUR"),
            InlineKeyboardButton("USD", callback_data="cur_USD"),
            InlineKeyboardButton("PLN", callback_data="cur_PLN"),
            InlineKeyboardButton("RUR", callback_data="cur_RUR"),
        ],
    ])


def _get_supplier_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора поставщика из БД."""
    try:
        suppliers = db.get_suppliers()
        buttons = []
        row = []
        for s in suppliers[:15]:
            row.append(InlineKeyboardButton(s["name"], callback_data=f"sup_{s['id']}"))
            if len(row) == 3:
                buttons.append(row)
                row = []
        if row:
            buttons.append(row)
        buttons.append([
            InlineKeyboardButton("➕ Новый поставщик", callback_data=CB_NEW_SUPPLIER),
            InlineKeyboardButton("⏭ Пропустить", callback_data=CB_SKIP),
        ])
        return InlineKeyboardMarkup(buttons)
    except Exception:
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ Новый поставщик", callback_data=CB_NEW_SUPPLIER)],
            [InlineKeyboardButton("⏭ Пропустить", callback_data=CB_SKIP)],
        ])


def _get_category_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора категории (все категории)."""
    try:
        categories = db.get_categories()
        buttons = []
        row = []
        for c in categories:
            row.append(InlineKeyboardButton(c["name"], callback_data=f"cat_{c['id']}"))
            if len(row) == 3:
                buttons.append(row)
                row = []
        if row:
            buttons.append(row)
        buttons.append([InlineKeyboardButton("⏭ Пропустить", callback_data=CB_SKIP)])
        return InlineKeyboardMarkup(buttons)
    except Exception:
        return InlineKeyboardMarkup([[InlineKeyboardButton("⏭ Пропустить", callback_data=CB_SKIP)]])


def _get_project_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора проекта/судна (все проекты)."""
    try:
        projects = db.get_projects()
        buttons = []
        row = []
        for p in projects:
            row.append(InlineKeyboardButton(p["name"], callback_data=f"proj_{p['id']}"))
            if len(row) == 3:
                buttons.append(row)
                row = []
        if row:
            buttons.append(row)
        buttons.append([InlineKeyboardButton("⏭ Пропустить", callback_data=CB_SKIP)])
        return InlineKeyboardMarkup(buttons)
    except Exception:
        return InlineKeyboardMarkup([[InlineKeyboardButton("⏭ Пропустить", callback_data=CB_SKIP)]])


def _get_payment_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора способа оплаты."""
    try:
        methods = db.get_payment_methods()
        buttons = []
        row = []
        for m in methods:
            row.append(InlineKeyboardButton(m["name"], callback_data=f"pay_{m['id']}"))
            if len(row) == 3:
                buttons.append(row)
                row = []
        if row:
            buttons.append(row)
        buttons.append([InlineKeyboardButton("⏭ Пропустить", callback_data=CB_SKIP)])
        return InlineKeyboardMarkup(buttons)
    except Exception:
        return InlineKeyboardMarkup([[InlineKeyboardButton("⏭ Пропустить", callback_data=CB_SKIP)]])


@dataclass
class SaveResult:
    """Результат сохранения в БД и Sheets."""
    document_id: int | None = None
    entry_id: int | None = None
    storage_url: str | None = None  # Public URL from Nextcloud
    sheets_synced: bool = False
    db_error: str | None = None
    storage_error: str | None = None
    sheets_error: str | None = None


async def _save_to_db_and_sheets(
    context: ContextTypes.DEFAULT_TYPE,
    parsed: ParsedData,
    upload_result: UploadResult,
    caption_raw: str,
    telegram_file_id: str | None = None,
    telegram_message_id: int | None = None,
    telegram_chat_id: int | None = None,
    original_filename: str | None = None,
    parse_status: str = "parsed",
) -> SaveResult:
    """
    Сохранить в PostgreSQL (primary) и Google Sheets (UI sync).
    
    Args:
        upload_result: Результат загрузки в Nextcloud
        
    Returns:
        SaveResult с document_id, entry_id, статусом синхронизации и ошибками.
    """
    result = SaveResult()
    result.storage_url = upload_result.public_url
    result.storage_error = upload_result.error if not upload_result.success else None
    
    # 1. Сохранить в PostgreSQL (PRIMARY storage)
    if config.DATABASE_URL:
        try:
            # Вставляем документ с новыми полями storage
            result.document_id = db.insert_document(
                telegram_file_id=telegram_file_id,
                telegram_message_id=telegram_message_id,
                telegram_chat_id=telegram_chat_id,
                original_filename=original_filename,
                caption_raw=caption_raw,
                # New storage fields
                storage_backend=upload_result.storage_backend,
                storage_path=upload_result.storage_path,
                public_url=upload_result.public_url,
                share_password=upload_result.share_password,
                upload_status="uploaded" if upload_result.success else "failed",
                upload_error=upload_result.error,
            )
            
            # Находим ID из справочников
            supplier_id = None
            if parsed.supplier:
                sup = db.find_supplier_by_name(parsed.supplier)
                if sup:
                    supplier_id = sup["id"]
            
            category_id = context.user_data.get("category_id")
            project_id = context.user_data.get("project_id")
            payment_method_id = context.user_data.get("payment_method_id")
            
            # Вычисляем total
            unit_price = parsed.unit_price or 0
            total = unit_price * parsed.qty
            
            # Вставляем запись расхода
            entry_data = db.ExpenseEntryData(
                expense_date=parsed.expense_date or date.today(),
                description=parsed.description or "No description",
                qty=parsed.qty,
                unit_price=parsed.unit_price,
                total=total,
                currency_code=parsed.currency,
                supplier_id=supplier_id,
                supplier_name_raw=parsed.supplier_raw or parsed.supplier,
                category_id=category_id,
                project_id=project_id,
                payment_method_id=payment_method_id,
                notes=parsed.notes,
                document_id=result.document_id,
                parse_source=parsed.parse_source,
                parse_status=parse_status,
                parse_confidence=parsed.confidence,
            )
            result.entry_id = db.insert_expense_entry(entry_data)
            logger.info(f"Saved to PostgreSQL: document_id={result.document_id}, entry_id={result.entry_id}")
        except Exception as e:
            logger.error(f"Failed to save to PostgreSQL: {e}")
            result.db_error = str(e)
    else:
        result.db_error = "DATABASE_URL not configured"
    
    # 2. Синхронизировать в Google Sheets (UI layer via Apps Script)
    try:
        unit_price = parsed.unit_price or 0
        total = unit_price * parsed.qty
        
        row_data = ExpenseRowData(
            expense_date=parsed.expense_date or date.today(),
            supplier=parsed.supplier or "",
            description=parsed.description or "",
            qty=parsed.qty,
            unit_price=unit_price,
            total=total,
            currency=parsed.currency or "EUR",
            category=context.user_data.get("category_name") or config.DEFAULT_CATEGORY,
            project=context.user_data.get("project_name") or config.DEFAULT_PROJECT,
            payment_method=context.user_data.get("payment_method_name"),
            notes=parsed.notes,
            document_url=upload_result.public_url,  # Nextcloud public URL
        )
        
        sheet_result = append_row_to_sheet(row_data)
        result.sheets_synced = sheet_result.success
        if not sheet_result.success:
            result.sheets_error = sheet_result.error
            logger.warning(f"Sheets sync failed: {sheet_result.error}")
        else:
            logger.info("Synced to Google Sheets via Apps Script")
    except Exception as e:
        logger.error(f"Failed to sync to Google Sheets: {e}")
        result.sheets_error = str(e)
    
    return result


async def _process_file(update: Update, context: ContextTypes.DEFAULT_TYPE, local_path: str, filename: str):
    """Обработка файла: парсинг, превью, ожидание подтверждения."""
    
    caption = update.message.caption or ""
    message = update.message
    
    # Сохраняем данные в context для callback
    context.user_data["local_path"] = local_path
    context.user_data["filename"] = filename
    context.user_data["caption_raw"] = caption
    context.user_data["telegram_file_id"] = getattr(message.document, "file_id", None) or (message.photo[-1].file_id if message.photo else None)
    context.user_data["telegram_message_id"] = message.message_id
    context.user_data["telegram_chat_id"] = message.chat.id
    
    status_msg = "📥 Файл получен, загружаю в Nextcloud..."
    if not DB_AVAILABLE:
        status_msg += "\n⚠️ PostgreSQL недоступен"
    await message.reply_text(status_msg)

    # 1) Upload to Nextcloud
    upload_result = upload_file_to_nextcloud(
        local_path=local_path,
        original_filename=filename,
    )
    
    context.user_data["upload_result"] = upload_result
    
    if not upload_result.success:
        logger.warning(f"Nextcloud upload failed: {upload_result.error}")
        # Не прерываем — продолжаем без файла, ошибка сохранится в БД
    
    file_url = upload_result.public_url or "(загрузка не удалась)"
    
    # 2) Если нет подписи — предложить диалог
    if not caption.strip():
        await message.reply_text(
            f"📎 Файл: {file_url}\n\n"
            f"Подписи нет. Как оформить запись?",
            reply_markup=_get_no_caption_keyboard()
        )
        return STATE_CONFIRM
    
    # 3) Парсим подпись
    try:
        suppliers_list = [s["name"] for s in db.get_suppliers()] if config.DATABASE_URL else None
    except Exception:
        suppliers_list = None
    
    parsed = parse_caption(caption, suppliers_from_db=suppliers_list)
    context.user_data["parsed"] = parsed
    
    # 4) Показываем превью
    preview = format_preview(parsed)
    
    storage_info = f"📎 {file_url}" if upload_result.success else f"⚠️ Файл не загружен: {upload_result.error}"
    
    if is_parse_sufficient(parsed):
        await message.reply_text(
            f"✅ Распознано:\n\n{preview}\n\n{storage_info}",
            reply_markup=_get_confirm_keyboard()
        )
    else:
        await message.reply_text(
            f"⚠️ Частично распознано:\n\n{preview}\n\n{storage_info}",
            reply_markup=_get_partial_keyboard()
        )
    
    return STATE_CONFIRM


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка документа."""
    logger.info(f"handle_document: chat_id={update.message.chat.id}, expected={config.GROUP_ID}")
    
    if update.message.chat.id != config.GROUP_ID:
        logger.info(f"Ignoring message from chat {update.message.chat.id} (not our group)")
        return ConversationHandler.END

    doc = update.message.document
    if not doc:
        logger.info("No document in message")
        return ConversationHandler.END
    
    logger.info(f"Processing document: {doc.file_name}")

    file_obj = await doc.get_file()
    filename = f"{doc.file_unique_id}_{doc.file_name}"
    local_path = os.path.join(config.DOWNLOAD_DIR, filename)

    await file_obj.download_to_drive(custom_path=local_path)
    return await _process_file(update, context, local_path, doc.file_name)


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка фото."""
    logger.info(f"handle_photo: chat_id={update.message.chat.id}, expected={config.GROUP_ID}")
    
    if update.message.chat.id != config.GROUP_ID:
        logger.info(f"Ignoring photo from chat {update.message.chat.id} (not our group)")
        return ConversationHandler.END

    if not update.message.photo:
        logger.info("No photo in message")
        return ConversationHandler.END

    logger.info("Processing photo...")
    photo = update.message.photo[-1]
    file_obj = await photo.get_file()

    filename = f"{photo.file_unique_id}.jpg"
    local_path = os.path.join(config.DOWNLOAD_DIR, filename)

    await file_obj.download_to_drive(custom_path=local_path)
    return await _process_file(update, context, local_path, filename)


async def callback_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка кнопок подтверждения."""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == CB_CANCEL:
        await query.edit_message_text("❌ Отменено")
        context.user_data.clear()
        return ConversationHandler.END
    
    if data == CB_SAVE or data == CB_SAVE_DRAFT:
        parsed = context.user_data.get("parsed")
        if not parsed:
            parsed = ParsedData(description="No description", expense_date=date.today())
        
        # Получаем upload_result из context (или создаём пустой если нет)
        upload_result = context.user_data.get("upload_result")
        if not upload_result:
            upload_result = UploadResult(success=False, error="No file uploaded")
        
        parse_status = "parsed" if data == CB_SAVE else "draft"
        
        save_result = await _save_to_db_and_sheets(
            context=context,
            parsed=parsed,
            upload_result=upload_result,
            caption_raw=context.user_data.get("caption_raw", ""),
            telegram_file_id=context.user_data.get("telegram_file_id"),
            telegram_message_id=context.user_data.get("telegram_message_id"),
            telegram_chat_id=context.user_data.get("telegram_chat_id"),
            original_filename=context.user_data.get("filename"),
            parse_status=parse_status,
        )
        
        status_emoji = "✅" if data == CB_SAVE else "📝"
        status_text = "Сохранено" if data == CB_SAVE else "Сохранено как черновик"
        
        result_text = f"{status_emoji} {status_text}\n\n"
        if parsed.description:
            result_text += f"📦 {parsed.description}\n"
        if parsed.unit_price:
            result_text += f"💰 {parsed.unit_price} {parsed.currency or ''}\n"
        if parsed.supplier:
            result_text += f"🏪 {parsed.supplier}\n"
        
        # Показываем ссылку на файл
        if save_result.storage_url:
            result_text += f"\n📎 {save_result.storage_url}"
        elif save_result.storage_error:
            result_text += f"\n⚠️ Файл: {save_result.storage_error}"
        
        if save_result.entry_id:
            result_text += f"\n🗃 DB entry: #{save_result.entry_id}"
        
        # Показываем статус синхронизации
        if save_result.db_error:
            result_text += f"\n\n⚠️ PostgreSQL: {save_result.db_error}"
        if save_result.sheets_error:
            result_text += f"\n⚠️ Sheets: {save_result.sheets_error}"
        elif save_result.sheets_synced:
            result_text += "\n✓ Sheets synced"
        
        await query.edit_message_text(result_text)
        context.user_data.clear()
        return ConversationHandler.END
    
    if data == CB_EDIT or data == CB_SHORT_FORM:
        await query.edit_message_text("📝 Введите описание товара/услуги:")
        return STATE_DESCRIPTION
    
    if data == CB_FULL_FORM:
        await query.edit_message_text("📝 Введите описание товара/услуги:")
        context.user_data["full_form"] = True
        return STATE_DESCRIPTION
    
    return STATE_CONFIRM


async def state_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получение описания."""
    text = update.message.text.strip()

    parsed = context.user_data.get("parsed") or ParsedData()
    parsed.description = text
    context.user_data["parsed"] = parsed

    await update.message.reply_text(
        "📅 Введите дату (ДД.ММ.ГГГГ) или выберите:",
        reply_markup=_get_date_keyboard()
    )
    return STATE_DATE


async def callback_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор даты (сегодня)."""
    query = update.callback_query
    await query.answer()
    
    parsed = context.user_data.get("parsed") or ParsedData()
    parsed.expense_date = date.today()
    context.user_data["parsed"] = parsed
    
    await query.edit_message_text("💰 Введите цену (например: 150 или 150.50):")
    return STATE_PRICE


async def state_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ввод даты вручную."""
    text = update.message.text.strip()
    
    parsed = context.user_data.get("parsed") or ParsedData()
    
    # Парсим дату в разных форматах
    for fmt in ["%d.%m.%Y", "%d/%m/%Y", "%Y-%m-%d", "%d.%m.%y", "%d/%m/%y"]:
        try:
            parsed.expense_date = date.fromisoformat(text) if fmt == "%Y-%m-%d" else \
                                  date(*(int(x) for x in (text.replace("/", ".").split(".")[::-1] if "." in text or "/" in text else [text[:4], text[4:6], text[6:]])))
        except Exception:
            pass
    
    # Простой парсинг
    import re
    match = re.match(r"(\d{1,2})[./](\d{1,2})[./](\d{2,4})", text)
    if match:
        d, m, y = int(match.group(1)), int(match.group(2)), int(match.group(3))
        if y < 100:
            y += 2000
        try:
            parsed.expense_date = date(y, m, d)
        except ValueError:
            pass
    
    if not parsed.expense_date:
        parsed.expense_date = date.today()
        await update.message.reply_text(f"⚠️ Не распознал дату, использую сегодня: {parsed.expense_date.strftime('%d.%m.%Y')}")
    
    context.user_data["parsed"] = parsed
    
    await update.message.reply_text("💰 Введите цену (например: 150 или 150.50):")
    return STATE_PRICE


async def state_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получение цены."""
    text = update.message.text.strip().replace(",", ".")
    
    try:
        price = float(text)
    except ValueError:
        await update.message.reply_text("❌ Неверный формат. Введите число (например: 150 или 150.50):")
        return STATE_PRICE
    
    parsed = context.user_data.get("parsed") or ParsedData()
    parsed.unit_price = price
    context.user_data["parsed"] = parsed
    
    await update.message.reply_text("💱 Выберите валюту:", reply_markup=_get_currency_keyboard())
    return STATE_CURRENCY


async def callback_currency(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор валюты."""
    query = update.callback_query
    await query.answer()
    
    currency = query.data.replace("cur_", "")
    
    parsed = context.user_data.get("parsed") or ParsedData()
    parsed.currency = currency
    context.user_data["parsed"] = parsed
    
    # Если короткая форма — сразу к поставщику
    if not context.user_data.get("full_form"):
        await query.edit_message_text("🏪 Выберите поставщика:", reply_markup=_get_supplier_keyboard())
        return STATE_SUPPLIER
    
    # Полная форма — спрашиваем количество
    await query.edit_message_text("🔢 Введите количество (или Enter для 1):")
    return STATE_QTY


async def state_qty(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получение количества."""
    text = update.message.text.strip()
    
    if not text or text == "-":
        qty = 1.0
    else:
        try:
            qty = float(text.replace(",", "."))
        except ValueError:
            await update.message.reply_text("❌ Неверный формат. Введите число:")
            return STATE_QTY
    
    parsed = context.user_data.get("parsed") or ParsedData()
    parsed.qty = qty
    context.user_data["parsed"] = parsed
    
    await update.message.reply_text("🏪 Выберите поставщика:", reply_markup=_get_supplier_keyboard())
    return STATE_SUPPLIER


async def callback_supplier(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор поставщика."""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == CB_SKIP:
        pass
    elif data == CB_NEW_SUPPLIER:
        await query.edit_message_text("🏪 Введите название нового поставщика:")
        return STATE_NEW_SUPPLIER
    elif data.startswith("sup_"):
        supplier_id = int(data.replace("sup_", ""))
        context.user_data["supplier_id"] = supplier_id
        try:
            suppliers = db.get_suppliers()
            for s in suppliers:
                if s["id"] == supplier_id:
                    parsed = context.user_data.get("parsed") or ParsedData()
                    parsed.supplier = s["name"]
                    context.user_data["parsed"] = parsed
                    break
        except Exception:
            pass
    
    # Если короткая форма — подтверждение
    if not context.user_data.get("full_form"):
        parsed = context.user_data.get("parsed") or ParsedData()
        preview = format_preview(parsed)
        await query.edit_message_text(
            f"📋 Проверьте данные:\n\n{preview}",
            reply_markup=_get_confirm_keyboard()
        )
        return STATE_CONFIRM
    
    # Полная форма — категория
    await query.edit_message_text("📁 Выберите категорию:", reply_markup=_get_category_keyboard())
    return STATE_CATEGORY


async def state_new_supplier(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ввод нового поставщика."""
    text = update.message.text.strip()
    
    if not text:
        await update.message.reply_text("❌ Название не может быть пустым. Введите название поставщика:")
        return STATE_NEW_SUPPLIER
    
    # Создаём нового поставщика в БД
    try:
        supplier_id = db.create_supplier_if_not_exists(text)
        context.user_data["supplier_id"] = supplier_id
        
        parsed = context.user_data.get("parsed") or ParsedData()
        parsed.supplier = text
        context.user_data["parsed"] = parsed
        
        await update.message.reply_text(f"✅ Поставщик '{text}' добавлен!")
    except Exception as e:
        logger.error(f"Failed to create supplier: {e}")
        parsed = context.user_data.get("parsed") or ParsedData()
        parsed.supplier = text
        parsed.supplier_raw = text
        context.user_data["parsed"] = parsed
        await update.message.reply_text(f"⚠️ Не удалось сохранить в БД, но продолжаем: {text}")
    
    # Если короткая форма — подтверждение
    if not context.user_data.get("full_form"):
        parsed = context.user_data.get("parsed") or ParsedData()
        preview = format_preview(parsed)
        await update.message.reply_text(
            f"📋 Проверьте данные:\n\n{preview}",
            reply_markup=_get_confirm_keyboard()
        )
        return STATE_CONFIRM
    
    # Полная форма — категория
    await update.message.reply_text("📁 Выберите категорию:", reply_markup=_get_category_keyboard())
    return STATE_CATEGORY


async def callback_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор категории."""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data != CB_SKIP and data.startswith("cat_"):
        category_id = int(data.replace("cat_", ""))
        context.user_data["category_id"] = category_id
        try:
            categories = db.get_categories()
            for c in categories:
                if c["id"] == category_id:
                    context.user_data["category_name"] = c["name"]
                    break
        except Exception:
            pass
    
    await query.edit_message_text("🚢 Выберите судно/проект:", reply_markup=_get_project_keyboard())
    return STATE_PROJECT


async def callback_project(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор проекта."""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data != CB_SKIP and data.startswith("proj_"):
        project_id = int(data.replace("proj_", ""))
        context.user_data["project_id"] = project_id
        try:
            projects = db.get_projects()
            for p in projects:
                if p["id"] == project_id:
                    context.user_data["project_name"] = p["name"]
                    break
        except Exception:
            pass
    
    await query.edit_message_text("💳 Выберите способ оплаты:", reply_markup=_get_payment_keyboard())
    return STATE_PAYMENT


async def callback_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор способа оплаты."""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data != CB_SKIP and data.startswith("pay_"):
        payment_id = int(data.replace("pay_", ""))
        context.user_data["payment_method_id"] = payment_id
    
    await query.edit_message_text("📝 Введите примечание (или '-' чтобы пропустить):")
    return STATE_NOTES


async def state_notes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получение примечания."""
    text = update.message.text.strip()
    
    if text and text != "-":
        parsed = context.user_data.get("parsed") or ParsedData()
        parsed.notes = text
        context.user_data["parsed"] = parsed
    
    # Показываем превью и подтверждение
    parsed = context.user_data.get("parsed") or ParsedData()
    preview = format_preview(parsed)
    
    await update.message.reply_text(
        f"📋 Проверьте данные:\n\n{preview}",
        reply_markup=_get_confirm_keyboard()
    )
    return STATE_CONFIRM


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена диалога."""
    await update.message.reply_text("❌ Отменено")
    context.user_data.clear()
    return ConversationHandler.END


def main():
    app = ApplicationBuilder().token(config.TELEGRAM_TOKEN).build()
    
    # ConversationHandler для обработки файлов с диалогом
    conv_handler = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Document.ALL, handle_document),
            MessageHandler(filters.PHOTO, handle_photo),
        ],
        states={
            STATE_CONFIRM: [
                CallbackQueryHandler(callback_confirm),
            ],
            STATE_DESCRIPTION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, state_description),
            ],
            STATE_DATE: [
                CallbackQueryHandler(callback_date, pattern=r"^date_today$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, state_date),
            ],
            STATE_PRICE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, state_price),
            ],
            STATE_CURRENCY: [
                CallbackQueryHandler(callback_currency, pattern=r"^cur_"),
            ],
            STATE_QTY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, state_qty),
            ],
        STATE_SUPPLIER: [
            CallbackQueryHandler(callback_supplier, pattern=r"^(sup_|skip|new_supplier)"),
        ],
        STATE_NEW_SUPPLIER: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, state_new_supplier),
        ],
            STATE_CATEGORY: [
                CallbackQueryHandler(callback_category, pattern=r"^(cat_|skip)"),
            ],
            STATE_PROJECT: [
                CallbackQueryHandler(callback_project, pattern=r"^(proj_|skip)"),
            ],
            STATE_PAYMENT: [
                CallbackQueryHandler(callback_payment, pattern=r"^(pay_|skip)"),
            ],
            STATE_NOTES: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, state_notes),
            ],
        },
        fallbacks=[
            MessageHandler(filters.COMMAND, cancel),
        ],
        per_message=False,
    )
    
    app.add_handler(conv_handler)
    
    # Проверка подключения к БД
    global DB_AVAILABLE
    if config.DATABASE_URL:
        if db.test_connection():
            DB_AVAILABLE = True
            logger.info("✅ PostgreSQL connection OK")
        else:
            DB_AVAILABLE = False
            logger.warning("⚠️ PostgreSQL connection FAILED")
    else:
        DB_AVAILABLE = False
        logger.warning("⚠️ DATABASE_URL not set")
    
    # Проверка Nextcloud
    from nextcloud_storage import test_connection as test_nextcloud
    if test_nextcloud():
        logger.info("✅ Nextcloud connection OK")
    else:
        logger.warning("⚠️ Nextcloud not available - files won't be uploaded")
    
    # Проверка Sheets Web App
    if config.SHEETS_WEBAPP_URL:
        logger.info(f"✅ Sheets Web App configured: {config.SHEETS_WEBAPP_URL[:50]}...")
    else:
        logger.warning("⚠️ SHEETS_WEBAPP_URL not set - Sheets sync disabled")
    
    print("Bear Supply bot started (v3 - Nextcloud + Apps Script)")
    if not DB_AVAILABLE:
        print("⚠️ WARNING: PostgreSQL unavailable!")
    app.run_polling(drop_pending_updates=True, allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
