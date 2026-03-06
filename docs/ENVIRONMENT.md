# Окружение развёртывания (DigitalOcean)

Временное окружение на дроплете DigitalOcean для тестирования доступа к Google Sheets и Google Drive.

## Сервер (дроплет)

| Параметр | Значение |
|----------|----------|
| **IP-адрес** | `104.248.84.119` |
| **Корневой каталог проекта** | `/opt/bear_supply/` |
| **Каталог с учётными данными** | `/opt/bear_supply/creds/` |
| **Файл ключа сервисного аккаунта** | `/opt/bear_supply/creds/google-sa.json` |

### Настройка ключа на сервере

```bash
cd /opt/bear_supply/creds
mv *.json google-sa.json
chmod 600 google-sa.json
```

- Права `600` — только владелец может читать/писать файл.

---

## Виртуальное окружение и зависимости

- **venv:** `/opt/bear_supply/creds/venv` (или по месту установки).
- Установленные пакеты:

```bash
pip install gspread google-auth google-api-python-client
```

| Пакет | Назначение |
|-------|------------|
| `gspread` | Работа с Google Sheets |
| `google-auth` | Аутентификация (сервисный аккаунт) |
| `google-api-python-client` | Клиент Google API (Sheets, Drive и др.) |

---

## Google Sheets

| Параметр | Значение |
|----------|----------|
| **Название** | BEAR_SUPPLY_2026 |
| **ID таблицы** | `1m6zvvp1CNaPknA7Y6FuIrLksm9b0cC4rU-R54H9LMug` |

- Открыть в браузере: `https://docs.google.com/spreadsheets/d/1m6zvvp1CNaPknA7Y6FuIrLksm9b0cC4rU-R54H9LMug`
- Сервисному аккаунту `bearsupply-bot@project-51e9ca8f-f0d1-4de7-9f1.iam.gserviceaccount.com` нужно выдать доступ к таблице (например, «Редактор» или «Читатель»).

---

## Google Drive

| Параметр | Значение |
|----------|----------|
| **Название каталога** | BEAR_SUPPLY |
| **ID каталога** | `1PNcDcQf09J4SlepPPUBNTaMnfEmmdOb2` |
| **Ссылка** | [drive.google.com/.../1PNcDcQf09J4SlepPPUBNTaMnfEmmdOb2](https://drive.google.com/drive/folders/1PNcDcQf09J4SlepPPUBNTaMnfEmmdOb2?usp=drive_link) |

- Сервисному аккаунту нужно выдать доступ к папке (например, через «Поделиться» → добавить почту бота с нужной ролью).

### Структура папок (результат загрузки через `drive_manager.py`)

При загрузке файлов через `upload_receipt()` в Google Drive создаётся иерархия **год → месяц**:

```
BEAR_SUPPLY
   └── 2026
        └── 2026-03
             amazon_invoice.txt
```

- Корень: каталог **BEAR_SUPPLY** (ID `1PNcDcQf09J4SlepPPUBNTaMnfEmmdOb2`).
- Внутри — папка по году (например, `2026`), в ней — папка по месяцу в формате `YYYY-MM` (например, `2026-03`).
- Загруженные файлы попадают в папку соответствующего месяца.

---

## OAuth для личного Google Drive (каталог BEAR_SUPPLY)

Для доступа к каталогу BEAR_SUPPLY на **личном** Google Drive используется OAuth (не сервисный аккаунт).

**Файл для авторизации:** `client_secret.json` лежит в **корневом каталоге проекта** и используется всеми скриптами OAuth.

| Файл | Назначение |
|------|-------------|
| `client_secret.json` | Учётные данные OAuth-приложения (в корне проекта). На сервере DO можно положить в `/opt/bear_supply/` или задать путь через `CLIENT_SECRET_JSON`. |
| `token.json` | Токен после авторизации через `auth_drive.py` (в корне). |
| `token.pickle` | Токен после авторизации через `drive_auth.py` (в корне или путь в `DRIVE_TOKEN_FILE`). |

**Скрипт проверки:** `scripts/drive_auth.py` — запускает поток OAuth, при первом запуске откроется авторизация в консоли; после успешного входа токен сохраняется в `token.pickle`.

```bash
python scripts/drive_auth.py
```

---

## Тестовый скрипт

В проекте есть скрипт проверки доступа к Sheets и Drive:

```bash
# На сервере (из корня проекта, с активированным venv)
cd /opt/bear_supply
source creds/venv/bin/activate
python scripts/test_google.py
```

Скрипт использует ключ из `GOOGLE_APPLICATION_CREDENTIALS` или по умолчанию `/opt/bear_supply/creds/google-sa.json`. Перед запуском выдайте сервисному аккаунту доступ к таблице и папке Drive.

---

## Telegram-бот bear_supply_bot

Бот — интерфейс между таблицей Google Sheets и пользователями: принимает фото и документы, загружает их в каталог BEAR_SUPPLY на Google Drive (структура год → месяц).

| Параметр | Значение |
|----------|----------|
| **Имя бота** | bear_supply_bot |
| **Группа для взаимодействия** | BEAR_SUPPLY (бот добавлен как администратор) |
| **ID группы** | `-5118688028` — бот обрабатывает фото и документы только в этой группе |
| **Скрипт** | `bear_supply_bot.py` |

### Переменные окружения

| Переменная | Назначение |
|------------|------------|
| **`BEAR_SUPPLY_TOKEN`** | Токен бота от [@BotFather](https://t.me/BotFather). **На дроплете в `.env` задаётся именно эта переменная.** |
| `BEAR_SUPPLY_GROUP_ID` | ID группы Telegram (по умолчанию `-5118688028`). |
| `BEAR_SUPPLY_SHEET_ID` | ID Google Sheet. |
| `BEAR_SUPPLY_WORKSHEET_NAME` | Имя листа (по умолчанию `Purchases_Log`). |
| `BEAR_SUPPLY_TOKEN_JSON` | Путь к `token.json` для Google API. |
| `BEAR_SUPPLY_DRIVE_FOLDER_ID` | ID папки на Google Drive для загрузки файлов. |

### Каталог загрузок

Временные файлы с Telegram сохраняются в `/opt/bear_supply/uploads` (создаётся автоматически). После загрузки в Drive файл остаётся на диске — при необходимости можно добавить удаление.

### Запуск

На дроплете токен задаётся в `.env` как **`BEAR_SUPPLY_TOKEN`**:

```bash
cd /opt/bear_supply
set -a
source /opt/bear_supply/.env
set +a
python3 /opt/bear_supply/bear_supply_bot.py
```

### Таблица Purchases_Log (по скрину)

- **Лист:** `Purchases_Log`.
- **Колонки, которые заполняет бот:** Date, Supplier, Description, Qty, Unit price, Currency, Document_Link.
- Остальные колонки (ID, Month, Platform, Total, Category, Project, Payment method, Invoice, Expense Type, Report_Key, Notes) в новой строке не заполняются (могут быть формулы или значения по умолчанию).

### Поведение

- **Фото** — сохраняются как `{file_unique_id}.jpg`, загружаются в Drive, пользователю отправляется ссылка.
- **Документы** — сохраняются под исходным именем, загружаются в Drive, отправляется ссылка.

---

*Окружение создано для тестирования; при необходимости обновляйте IP и пути.*
