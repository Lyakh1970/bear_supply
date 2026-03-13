# Структура базы данных PostgreSQL

**База:** `defaultdb` (Digital Ocean Managed Database)  
**Владелец:** `doadmin`

---

## Обзор таблиц

| Таблица | Назначение |
|---------|------------|
| `expense_entries` | Основная таблица — записи расходов |
| `suppliers` | Справочник поставщиков |
| `categories` | Справочник категорий расходов |
| `projects` | Справочник проектов |
| `payment_methods` | Справочник способов оплаты |
| `currencies` | Справочник валют |
| `documents` | Загруженные документы (файлы из Telegram) |

---

## Диаграмма связей

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   suppliers     │     │   categories    │     │    projects     │
│─────────────────│     │─────────────────│     │─────────────────│
│ id (PK)         │     │ id (PK)         │     │ id (PK)         │
│ name            │     │ name            │     │ name            │
│ supplier_type   │     │ created_at      │     │ created_at      │
│ country_code    │     └────────┬────────┘     └────────┬────────┘
│ created_at      │              │                       │
└────────┬────────┘              │                       │
         │                       │                       │
         │              ┌────────┴───────────────────────┘
         │              │
         ▼              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        expense_entries                           │
│─────────────────────────────────────────────────────────────────│
│ id (PK)              │ supplier_id (FK)      │ category_id (FK) │
│ expense_date         │ supplier_name_raw     │ project_id (FK)  │
│ month_key            │ description           │ document_id (FK) │
│ qty, unit_price      │ currency_code (FK)    │ payment_method_id│
│ total                │ parse_status          │ report_key       │
└─────────────────────────────────────────────────────────────────┘
         │                       │
         │                       ▼
         │              ┌─────────────────┐     ┌─────────────────┐
         │              │   currencies    │     │ payment_methods │
         │              │─────────────────│     │─────────────────│
         │              │ code (PK)       │     │ id (PK)         │
         │              │ name            │     │ name            │
         │              └─────────────────┘     │ created_at      │
         │                                      └─────────────────┘
         ▼
┌─────────────────────────────────────────┐
│              documents                   │
│─────────────────────────────────────────│
│ id (PK)           │ drive_url           │
│ telegram_file_id  │ caption_raw         │
│ telegram_msg_id   │ ocr_text_raw        │
│ original_filename │ uploaded_at         │
│ mime_type         │                     │
└─────────────────────────────────────────┘
```

---

## Таблицы

### 1. `expense_entries` — Записи расходов

Основная таблица для хранения данных о покупках/расходах.

| Колонка | Тип | Nullable | Default | Описание |
|---------|-----|----------|---------|----------|
| `id` | bigserial | NOT NULL | auto | Первичный ключ |
| `expense_date` | date | NOT NULL | CURRENT_DATE | Дата расхода |
| `month_key` | text | NOT NULL | — | Ключ месяца (напр. `2026-03`) |
| `supplier_id` | bigint | NULL | — | FK → suppliers.id |
| `supplier_name_raw` | text | NULL | — | Исходное имя поставщика (до нормализации) |
| `description` | text | NOT NULL | — | Описание товара/услуги |
| `qty` | numeric(12,3) | NOT NULL | 1 | Количество |
| `unit_price` | numeric(14,2) | NULL | — | Цена за единицу |
| `total` | numeric(14,2) | NULL | — | Общая сумма |
| `currency_code` | text | NULL | — | FK → currencies.code |
| `category_id` | bigint | NULL | — | FK → categories.id |
| `project_id` | bigint | NULL | — | FK → projects.id |
| `payment_method_id` | bigint | NULL | — | FK → payment_methods.id |
| `invoice` | text | NULL | — | Номер счёта/инвойса |
| `expense_type` | text | NULL | — | Тип расхода |
| `report_key` | text | NULL | — | Ключ для отчётов |
| `notes` | text | NULL | — | Примечания |
| `document_id` | bigint | NULL | — | FK → documents.id |
| `parse_source` | text | NULL | — | Источник парсинга (telegram, manual и т.д.) |
| `parse_status` | text | NOT NULL | 'draft' | Статус: draft, verified, error |
| `parse_confidence` | numeric(5,2) | NULL | — | Уверенность парсинга (0-100%) |
| `created_at` | timestamptz | NOT NULL | now() | Дата создания записи |
| `updated_at` | timestamptz | NOT NULL | now() | Дата обновления записи |

**Индексы:**
- `expense_entries_pkey` — PRIMARY KEY (id)

**Foreign Keys:**
- `supplier_id` → `suppliers(id)`
- `currency_code` → `currencies(code)`
- `category_id` → `categories(id)`
- `project_id` → `projects(id)`
- `payment_method_id` → `payment_methods(id)`
- `document_id` → `documents(id)`

---

### 2. `suppliers` — Поставщики

| Колонка | Тип | Nullable | Default | Описание |
|---------|-----|----------|---------|----------|
| `id` | bigserial | NOT NULL | auto | Первичный ключ |
| `name` | text | NOT NULL | — | Название поставщика (уникальное) |
| `supplier_type` | text | NULL | — | Тип (vendor, marketplace, etc.) |
| `country_code` | text | NULL | — | Код страны (ISO 3166-1 alpha-2) |
| `created_at` | timestamptz | NOT NULL | now() | Дата создания |

**Ограничения:** `name` UNIQUE

---

### 3. `categories` — Категории

| Колонка | Тип | Nullable | Default | Описание |
|---------|-----|----------|---------|----------|
| `id` | bigserial | NOT NULL | auto | Первичный ключ |
| `name` | text | NOT NULL | — | Название категории (уникальное) |
| `created_at` | timestamptz | NOT NULL | now() | Дата создания |

**Ограничения:** `name` UNIQUE

---

### 4. `projects` — Проекты

| Колонка | Тип | Nullable | Default | Описание |
|---------|-----|----------|---------|----------|
| `id` | bigserial | NOT NULL | auto | Первичный ключ |
| `name` | text | NOT NULL | — | Название проекта (уникальное) |
| `created_at` | timestamptz | NOT NULL | now() | Дата создания |

**Ограничения:** `name` UNIQUE

---

### 5. `payment_methods` — Способы оплаты

| Колонка | Тип | Nullable | Default | Описание |
|---------|-----|----------|---------|----------|
| `id` | bigserial | NOT NULL | auto | Первичный ключ |
| `name` | text | NOT NULL | — | Название (Cash, Card, Transfer и т.д.) |
| `created_at` | timestamptz | NOT NULL | now() | Дата создания |

**Ограничения:** `name` UNIQUE

---

### 6. `currencies` — Валюты

| Колонка | Тип | Nullable | Default | Описание |
|---------|-----|----------|---------|----------|
| `code` | text | NOT NULL | — | Код валюты (EUR, USD, PLN) — PRIMARY KEY |
| `name` | text | NULL | — | Полное название валюты |

**Текущие данные:**
```sql
INSERT INTO currencies (code, name) VALUES
('EUR', 'Euro'),
('USD', 'US Dollar'),
('PLN', 'Polish Zloty'),
('RUR', 'Russian Ruble');
```

---

### 7. `documents` — Документы

Хранит метаданные файлов, загруженных через Telegram.

| Колонка | Тип | Nullable | Default | Описание |
|---------|-----|----------|---------|----------|
| `id` | bigserial | NOT NULL | auto | Первичный ключ |
| `telegram_file_id` | text | NULL | — | ID файла в Telegram |
| `telegram_message_id` | bigint | NULL | — | ID сообщения в Telegram |
| `telegram_chat_id` | bigint | NULL | — | ID чата в Telegram |
| `original_filename` | text | NULL | — | Исходное имя файла |
| `mime_type` | text | NULL | — | MIME-тип (image/jpeg, application/pdf) |
| `file_size_bytes` | bigint | NULL | — | Размер файла в байтах |
| `drive_url` | text | NULL | — | Ссылка на файл в Google Drive |
| `caption_raw` | text | NULL | — | Исходный текст подписи из Telegram |
| `ocr_text_raw` | text | NULL | — | Распознанный текст (OCR) |
| `uploaded_at` | timestamptz | NOT NULL | now() | Дата загрузки |

---

## SQL для создания таблиц

```sql
-- Справочники
CREATE TABLE IF NOT EXISTS suppliers (
    id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    supplier_type TEXT,
    country_code TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS categories (
    id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS projects (
    id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS payment_methods (
    id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS currencies (
    code TEXT PRIMARY KEY,
    name TEXT
);

-- Документы
CREATE TABLE IF NOT EXISTS documents (
    id BIGSERIAL PRIMARY KEY,
    telegram_file_id TEXT,
    telegram_message_id BIGINT,
    telegram_chat_id BIGINT,
    original_filename TEXT,
    mime_type TEXT,
    file_size_bytes BIGINT,
    drive_url TEXT,
    caption_raw TEXT,
    ocr_text_raw TEXT,
    uploaded_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Основная таблица расходов
CREATE TABLE IF NOT EXISTS expense_entries (
    id BIGSERIAL PRIMARY KEY,
    expense_date DATE NOT NULL DEFAULT CURRENT_DATE,
    month_key TEXT NOT NULL,

    supplier_id BIGINT REFERENCES suppliers(id),
    supplier_name_raw TEXT,

    description TEXT NOT NULL,

    qty NUMERIC(12,3) NOT NULL DEFAULT 1,
    unit_price NUMERIC(14,2),
    total NUMERIC(14,2),

    currency_code TEXT REFERENCES currencies(code),

    category_id BIGINT REFERENCES categories(id),
    project_id BIGINT REFERENCES projects(id),
    payment_method_id BIGINT REFERENCES payment_methods(id),

    invoice TEXT,
    expense_type TEXT,
    report_key TEXT,
    notes TEXT,

    document_id BIGINT REFERENCES documents(id),

    parse_source TEXT,
    parse_status TEXT NOT NULL DEFAULT 'draft',
    parse_confidence NUMERIC(5,2),

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

---

## Данные справочников

### payment_methods

| id | name |
|----|------|
| 1 | Company Card |
| 2 | Personal Card |
| 3 | Bank Transfer |
| 4 | Cash |
| 5 | Online Payment |

### categories

| id | name |
|----|------|
| 1 | IT Hardware |
| 2 | IT Services |
| 3 | Electronics |
| 4 | Ship Equipment |
| 5 | 3D Printing |
| 6 | Office |
| 7 | Tools |
| 8 | Subscriptions |
| 9 | Travel |
| 10 | Fuel |
| 11 | Accommodation |
| 12 | Logistics |
| 13 | Software |

### projects

| id | name |
|----|------|
| 1 | General |
| 2 | Fishing Success |
| 3 | Fishing Vest |
| 4 | Fishing Sea |
| 5 | Fishing Koral |
| 6 | Kapitan Morgun |
| 7 | Fishing Force |
| 8 | Fishing Tide |
| 9 | Scombrus |
| 10 | Harengus |
| 11 | SkladLP |
| 12 | OfficeKLD |

### suppliers

| id | name | supplier_type | country_code |
|----|------|---------------|--------------|
| 1 | amazon.es | marketplace | ES |
| 2 | amazon.pl | marketplace | PL |
| 3 | allegro.pl | marketplace | PL |
| 4 | canaryonline | store | ES |
| 5 | Sugraher | store | ES |
| 6 | PCComponente | store | ES |
| 7 | AliExpress | marketplace | CN |
| 8 | Temu | marketplace | CN |
| 9 | DigitalOcean | service | US |
| 10 | ZeroTier | service | US |
| 11 | OpenAI | service | US |
| 12 | Microsoft | service | US |
| 13 | Vesselfinder | service | US |
| 14 | Maritime Optima | service | US |

### currencies

| code | name |
|------|------|
| EUR | Euro |
| USD | US Dollar |
| PLN | Polish Zloty |
| RUR | Russian Ruble |

---

## Подключение

```bash
# Из .env
set -a && source /opt/bear_supply/.env && set +a
psql "$DATABASE_URL"
```

**Переменная окружения:**
```
DATABASE_URL=postgresql://doadmin:PASSWORD@host:25060/defaultdb?sslmode=require
```
