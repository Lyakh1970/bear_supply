# Данные проекта Google Cloud — Bear-Supply

Документация настроек проекта в Google Cloud Console (раздел IAM & Admin → Settings).

## Основные данные проекта

| Параметр | Значение |
|----------|----------|
| **Название проекта (Project name)** | Bear-Supply |
| **Идентификатор проекта (Project ID)** | `project-51e9ca8f-f0d1-4de7-9f1` |
| **Номер проекта (Project number)** | `30844631958` |
| **Местоположение (Location)** | `440732814695` |

## Платежи и биллинг

- **Платежный аккаунт (Billing Account):** настраивается через ссылку «Manage billing» (Управление платежами) в консоли.

## Прозрачность доступа (Access Transparency)

Access Transparency недоступна для проектов, не входящих в организацию.  
Чтобы включить прозрачность доступа для одного проекта, нужно обратиться в отдел продаж или в поддержку Google.

---

## Включённые API

| API | Назначение |
|-----|------------|
| **Google Sheets API** | Работа с таблицами Google Sheets |
| **Google Drive API** | Доступ к файлам и папкам в Google Drive |

---

## Сервисный аккаунт (бот)

Используется для автоматизации доступа к Google Sheets и Google Drive без входа пользователя.

| Параметр | Значение |
|----------|----------|
| **Имя (Service account name)** | bearsupply-bot |
| **ID (Service account ID)** | bearsupply-bot |
| **Email (почта бота)** | `bearsupply-bot@project-51e9ca8f-f0d1-4de7-9f1.iam.gserviceaccount.com` |
| **Описание** | BEAR SUPPLY automation bot |

### JSON-ключи

После создания сервисного аккаунта в консоли создаются **JSON-ключи** (Keys) для аутентификации в коде.

- Хранить файл ключа в безопасном месте, **не коммитить** в репозиторий.
- Добавить путь к ключу в `.gitignore` (например: `*-credentials.json`, `secrets/`).
- В коде использовать переменную окружения или путь к файлу для загрузки ключа.

**На сервере DO:** ключ сохранён как `/opt/bear_supply/creds/google-sa.json` (см. [Окружение развёртывания](ENVIRONMENT.md)).

*Когда JSON-ключ будет создан, можно добавить сюда примечание о месте хранения (например, локальный путь или секрет в CI/CD).*

---

## Ресурсы (таблица и каталог Drive)

| Ресурс | Название | ID |
|--------|----------|-----|
| **Google Sheets** | BEAR_SUPPLY_2026 | `1m6zvvp1CNaPknA7Y6FuIrLksm9b0cC4rU-R54H9LMug` |
| **Google Drive (папка)** | BEAR_SUPPLY | `1PNcDcQf09J4SlepPPUBNTaMnfEmmdOb2` |

Подробности по окружению и ссылкам — в [ENVIRONMENT.md](ENVIRONMENT.md).

---

*Данные взяты из Google Cloud Console. Обновлено по состоянию на момент документирования.*
