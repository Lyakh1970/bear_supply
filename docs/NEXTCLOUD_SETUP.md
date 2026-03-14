# Настройка Nextcloud для Bear Supply Bot

**Сервер:** `cloud.bearcloud.one`  
**Пользователь:** `bearbot`  
**Папка:** `Documents/BearBox Docs/Finance`

---

## Шаг 1. Создание App Password

1. Зайти под `bearbot` в веб-интерфейс https://cloud.bearcloud.one
2. Аватар справа вверху → **Personal settings** → **Security**
3. Создать **App password** с именем: `bear_supply_bot`
4. Сохранить сгенерированный пароль (показывается только один раз)

> WebDAV и сторонние клиенты Nextcloud требуют app password, а не обычный пароль.

---

## Шаг 2. Подготовка папки

Создать папку в веб-интерфейсе:
```
Documents / BearBox Docs / Finance
```

Бот будет загружать файлы сюда с автоматической структурой `YYYY/MM/`.

---

## Шаг 3. Проверка WebDAV доступа

URL для пользователя `bearbot`:
```
https://cloud.bearcloud.one/remote.php/dav/files/bearbot/
```

Проверка из терминала:
```bash
curl -u 'bearbot:APP_PASSWORD' -X PROPFIND \
  'https://cloud.bearcloud.one/remote.php/dav/files/bearbot/' \
  -H 'Depth: 0'
```

Успех: XML-ответ с `<d:multistatus>`.

---

## Шаг 4. Проверка Share API

### Создание public link (с паролем — обязательно по политике сервера):

```bash
curl -u 'bearbot:APP_PASSWORD' \
  -H 'OCS-APIRequest: true' \
  -d 'path=/Documents/BearBox Docs/Finance/test_nc.txt' \
  -d 'shareType=3' \
  -d 'password=BearBox2026!' \
  'https://cloud.bearcloud.one/ocs/v2.php/apps/files_sharing/api/v1/shares'
```

Успех: XML с `<url>https://cloud.bearcloud.one/s/XXXXX</url>`.

### Если требуется срок действия:

```bash
curl -u 'bearbot:APP_PASSWORD' \
  -H 'OCS-APIRequest: true' \
  -d 'path=/Documents/BearBox Docs/Finance/test_nc.txt' \
  -d 'shareType=3' \
  -d 'password=BearBox2026!' \
  -d 'expireDate=2026-12-31' \
  'https://cloud.bearcloud.one/ocs/v2.php/apps/files_sharing/api/v1/shares'
```

---

## Политика безопасности сервера

На `cloud.bearcloud.one` включена политика:
- **Passwords are enforced for link and mail shares**

Это означает:
- Публичные ссылки без пароля создать нельзя
- Бот должен передавать `password=` при создании share
- Пароль нужно сохранять в БД для последующего доступа

### Рекомендуемые настройки (Administration settings → Sharing):

| Опция | Значение |
|-------|----------|
| Allow apps to use the Share API | ✅ включено |
| Allow users to share via link and email | ✅ включено |
| Enforce password protection | ✅ включено (политика) |
| Enforce expiration date | по желанию |

---

## Переменные окружения (.env)

```bash
NEXTCLOUD_BASE_URL=https://cloud.bearcloud.one
NEXTCLOUD_USERNAME=bearbot
NEXTCLOUD_PASSWORD=NHEgM-xxxxx-xxxxx-xxxxx-xxxxx  # App Password
NEXTCLOUD_BASE_FOLDER=Documents/BearBox Docs/Finance
NEXTCLOUD_SHARE_PASSWORD=BearBox2026!  # Пароль для public links
```

---

## Схема работы бота

```
1. Telegram → файл получен
2. WebDAV PUT → загрузка в Nextcloud
   URL: /remote.php/dav/files/bearbot/Documents/BearBox Docs/Finance/2026/03/file.pdf
3. OCS Share API → создание public link с паролем
   POST /ocs/v2.php/apps/files_sharing/api/v1/shares
4. PostgreSQL → сохранение:
   - storage_backend = 'nextcloud'
   - storage_path = '/Documents/BearBox Docs/Finance/2026/03/file.pdf'
   - public_url = 'https://cloud.bearcloud.one/s/XXXXX'
   - share_password = 'BearBox2026!'
   - upload_status = 'uploaded'
5. Google Sheets → UI-витрина с public_url
```

---

## SQL миграция

```sql
-- Добавить поля для Nextcloud storage
ALTER TABLE documents
ADD COLUMN IF NOT EXISTS storage_backend TEXT,
ADD COLUMN IF NOT EXISTS storage_path TEXT,
ADD COLUMN IF NOT EXISTS public_url TEXT,
ADD COLUMN IF NOT EXISTS upload_status TEXT DEFAULT 'pending',
ADD COLUMN IF NOT EXISTS upload_error TEXT,
ADD COLUMN IF NOT EXISTS share_password TEXT;
```

---

## Тестирование

### 1. Проверка WebDAV:
```bash
curl -u 'bearbot:APP_PASSWORD' -X PROPFIND \
  'https://cloud.bearcloud.one/remote.php/dav/files/bearbot/Documents/BearBox%20Docs/Finance/' \
  -H 'Depth: 1'
```

### 2. Загрузка файла:
```bash
curl -u 'bearbot:APP_PASSWORD' -X PUT \
  --data-binary @test.txt \
  'https://cloud.bearcloud.one/remote.php/dav/files/bearbot/Documents/BearBox%20Docs/Finance/test.txt'
```

### 3. Создание share:
```bash
curl -u 'bearbot:APP_PASSWORD' \
  -H 'OCS-APIRequest: true' \
  -d 'path=/Documents/BearBox Docs/Finance/test.txt' \
  -d 'shareType=3' \
  -d 'password=BearBox2026!' \
  'https://cloud.bearcloud.one/ocs/v2.php/apps/files_sharing/api/v1/shares'
```

---

## Troubleshooting

| Ошибка | Причина | Решение |
|--------|---------|---------|
| 401 Unauthorized | Неверный app password | Пересоздать app password |
| 403 Passwords are enforced | Политика сервера | Передавать password= в API |
| 404 Not Found | Папка не существует | Создать папку или проверить путь |
| 507 Insufficient Storage | Нет места | Проверить квоту пользователя |
