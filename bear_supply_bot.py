import os
import logging
from pathlib import Path

from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

import config
from parser import parse_caption
from drive_manager import upload_to_drive
from sheets_manager import append_purchase

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)

Path(config.DOWNLOAD_DIR).mkdir(parents=True, exist_ok=True)


async def _process(update: Update, context: ContextTypes.DEFAULT_TYPE, local_path: str, filename: str):

    caption = update.message.caption or ""

    await update.message.reply_text("Файл получен, загружаю в Drive...")

    # 1) Upload to Drive
    document_link = upload_to_drive(
        token_json_path=config.TOKEN_JSON,
        local_path=local_path,
        filename=filename,
        folder_id=(config.DRIVE_FOLDER_ID or None)
    )

    # 2) Parse caption
    try:
        p = parse_caption(caption)
    except Exception as e:
        await update.message.reply_text(
            f"Документ сохранён\n{document_link}\n\n"
            f"⚠️ Не смог распарсить подпись: {e}\n"
            f"Формат:\nSupplier; Description; 120€\n"
            f"или\nSupplier; Description; Qty; 120€"
        )
        return

    # 3) Append to Google Sheet
    try:
        append_purchase(
            token_json_path=config.TOKEN_JSON,
            sheet_id=config.SHEET_ID,
            worksheet_name=config.WORKSHEET_NAME,
            supplier=p.supplier,
            description=p.description,
            qty=p.qty,
            unit_price=p.price,
            currency=p.currency,
            document_link=document_link
        )
    except Exception as e:
        await update.message.reply_text(
            f"Документ сохранён\n{document_link}\n\n"
            f"⚠️ Caption распарсен, но записать в таблицу не смог:\n{e}"
        )
        return

    await update.message.reply_text(
        f"✅ Готово\n{document_link}\n\n"
        f"{p.supplier}; {p.description}; qty={p.qty}; {p.price} {p.currency}"
    )


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat.id != config.GROUP_ID:
        return

    doc = update.message.document
    if not doc:
        return

    file_obj = await doc.get_file()
    filename = f"{doc.file_unique_id}_{doc.file_name}"
    local_path = os.path.join(config.DOWNLOAD_DIR, filename)

    await file_obj.download_to_drive(custom_path=local_path)
    await _process(update, context, local_path, doc.file_name)


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat.id != config.GROUP_ID:
        return

    if not update.message.photo:
        return

    photo = update.message.photo[-1]
    file_obj = await photo.get_file()

    filename = f"{photo.file_unique_id}.jpg"
    local_path = os.path.join(config.DOWNLOAD_DIR, filename)

    await file_obj.download_to_drive(custom_path=local_path)
    await _process(update, context, local_path, filename)


def main():
    app = ApplicationBuilder().token(config.TELEGRAM_TOKEN).build()

    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    print("Bear Supply bot started")
    app.run_polling(drop_pending_updates=True, allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()