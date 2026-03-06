# Анализ проблем и сценария работы бота

## Ожидаемый сценарий

1. В группе Telegram **bear_supply** пользователь отправляет **фото или PDF** с подписью (caption) вида:  
   `Amazon; SSD Samsung 1TB; 2; 120€`
2. Бот отвечает ссылкой на файл в Google Drive.
3. Бот пишет «✅ Готово».
4. В Google Sheet добавляется строка по заголовкам: **Supplier**, **Description**, **Qty**, **Unit price**, **Currency**, **Document_Link** (ссылка на документ). Остальные колонки (ID, Month, Platform, Total, Category, Project, Payment method, Invoice, Expense Type, Report_Key, Notes) бот не заполняет — в них могут быть формулы или значения по умолчанию.

---

## Исправленные проблемы

### 1. Импорт `parser` — **критично (исправлено)**

- **Было:** в проекте файл назывался `parcer.py` (опечатка), а в `bear_supply_bot.py` импорт: `from parser import parse_caption`.
- **Следствие:** при запуске бота возникала ошибка `ModuleNotFoundError: No module named 'parser'`.
- **Исправление:** файл переименован в `parser.py`, импорт теперь работает.

### 2. Токен Telegram не подхватывался из `.env` — **критично (исправлено)**

- **Было:** в `config.py` читается переменная `BEAR_SUPPLY_TOKEN`, а в `.env` локально была задана `TELEGRAM_BOT_TOKEN`.
- **Следствие:** после `source .env` переменная `BEAR_SUPPLY_TOKEN` не установлена → при старте бота: `RuntimeError: Env BEAR_SUPPLY_TOKEN is not set`.
- **Исправление:** в `config.py` токен берётся из `BEAR_SUPPLY_TOKEN` или из `TELEGRAM_BOT_TOKEN`. **На дроплете в `.env` используется переменная `BEAR_SUPPLY_TOKEN`** — так и должно быть.

---

## Что проверить вручную

### 3. Имя листа (worksheet) в Google Sheet

- Лист, с которым работает бот: **`Purchases_Log`** (как на скрине).
- В `config.py` по умолчанию: `WORKSHEET_NAME = "Purchases_Log"`. Если на дроплете нужно другое имя — задайте в `.env`: `BEAR_SUPPLY_WORKSHEET_NAME=...`.

### 4. Заголовки в первой строке листа (по скрину)

- На листе **Purchases_Log** колонки (слева направо):  
  **ID**, **Date**, **Month**, **Supplier**, **Platform**, **Description**, **Qty**, **Unit price**, **Total**, **Currency**, **Category**, **Project**, **Payment method**, **Invoice**, **Expense Type**, **Report_Key**, **Notes**, **Document_Link**.
- Бот заполняет только: **Date**, **Supplier**, **Description**, **Qty**, **Unit price**, **Currency**, **Document_Link**. Остальные столбцы (ID, Month, Platform, Total, Category, Project, Payment method, Invoice, Expense Type, Report_Key, Notes) в новой строке остаются пустыми или с формулами — так и задумано.
- В `sheets_manager.py` заголовки ищутся по псевдонимам (без учёта регистра): `Supplier`, `Description`, `Qty`, `Unit price`, `Currency`, `Document_Link` — с вашим скрином совпадают.

### 5. Формат `token.json` для Google API

- `google_auth.py` загружает учётные данные через `Credentials.from_authorized_user_info(data, scopes=SCOPES)`.
- Файл `token.json` должен быть в формате, который понимает этот метод (поля вроде `token`/`access_token`, `refresh_token`, `client_id`, `client_secret` и т.д.).
- Если `token.json` был сохранён через `auth_drive.py` (метод `creds.to_json()`), формат обычно совместим. Если файл получен или правился вручную, при ошибках вида «invalid grant» или «Credentials format» стоит переполучить токен через `auth_drive.py` и не менять структуру JSON.

### 6. Доступ к таблице и Drive от аккаунта из `token.json`

- Тот Google-аккаунт, от которого получен `token.json`, должен иметь:
  - доступ к нужной Google Sheet (как минимум редактор);
  - доступ к папке на Drive (куда загружаются файлы), если задан `BEAR_SUPPLY_DRIVE_FOLDER_ID`.
- Иначе возможны 404 или «permission denied» при загрузке в Drive или при записи в таблицу.

### 7. Подпись (caption) к фото/документу

- Парсер ожидает подпись в формате:
  - `Поставщик; Описание; Цена` (например, `Amazon; SSD 1TB; 120€`) — тогда Qty = 1;
  - или `Поставщик; Описание; Количество; Цена` (например, `Amazon; SSD Samsung 1TB; 2; 120€`).
- Разделитель — точка с запятой (`;`). Пробелы до/после частей допускаются.
- Если подпись пустая или в другом формате, бот всё равно загрузит файл в Drive и отправит ссылку, но напишет, что не удалось распарсить подпись и не добавит строку в таблицу.

---

## Запуск (напоминание)

```bash
cd /opt/bear_supply
set -a
source /opt/bear_supply/.env
set +a
python3 /opt/bear_supply/bear_supply_bot.py
```

Убедитесь, что в `.env` на дроплете заданы:

- **`BEAR_SUPPLY_TOKEN`** — токен бота (на дроплете используется именно эта переменная);
- `BEAR_SUPPLY_SHEET_ID` — ID таблицы;
- при необходимости `BEAR_SUPPLY_DRIVE_FOLDER_ID` — ID папки на Drive;
- при необходимости `BEAR_SUPPLY_WORKSHEET_NAME` — имя листа (по умолчанию `Purchases_Log`, как на скрине).

---

## Структура файлов на сервере

```
/opt/bear_supply/
  config.py
  parser.py
  google_auth.py
  drive_manager.py
  sheets_manager.py
  bear_supply_bot.py
  .env
  creds/
    token.json
  uploads/   # создаётся ботом для временных файлов
```
