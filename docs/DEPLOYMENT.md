# Развёртывание: GitHub → DigitalOcean

Репозиторий: **https://github.com/Lyakh1970/bear_supply.git**

---

## 1. Коммит и пуш с локальной машины

**Важно:** в репозиторий **не попадают** (см. `.gitignore`): `.env`, `token.json`, `client_secret.json`, папки `creds/`, `uploads/`. Секреты на сервере задаются отдельно.

```bash
cd /path/to/BEAR_SUPPLY

# Если репозиторий ещё не инициализирован:
git init
git remote add origin https://github.com/Lyakh1970/bear_supply.git

# Добавить файлы и закоммитить
git add .
git status   # убедиться, что .env и creds/ не в списке
git commit -m "Initial: bot, Drive, Sheets, parser, config"

# Пуш (при первом разе может понадобиться авторизация GitHub)
git branch -M main
git push -u origin main
```

Дальнейшие изменения:

```bash
git add .
git commit -m "Описание изменений"
git push
```

---

## 2. Развёртывание на дроплете DO

На сервере (Ubuntu) один раз настраиваем клон и окружение, затем обновляем код через `git pull`.

### Первоначальная настройка на DO

```bash
# Клонировать репозиторий
sudo mkdir -p /opt
sudo git clone https://github.com/Lyakh1970/bear_supply.git /opt/bear_supply
cd /opt/bear_supply

# Виртуальное окружение и зависимости
sudo python3 -m venv /opt/bear_supply/venv
sudo /opt/bear_supply/venv/bin/pip install --upgrade pip
sudo /opt/bear_supply/venv/bin/pip install -r requirements.txt
```

Если `python3 -m venv` не найден: `sudo apt update && sudo apt install -y python3-venv python3-pip`, затем снова команды выше.

**Если папки `venv` ещё нет** (например, клон был без настройки), выполните только блок про venv и зависимости:

```bash
cd /opt/bear_supply
python3 -m venv /opt/bear_supply/venv
/opt/bear_supply/venv/bin/pip install --upgrade pip
/opt/bear_supply/venv/bin/pip install -r requirements.txt
```

# Каталоги для секретов и загрузок

```bash
sudo mkdir -p /opt/bear_supply/creds /opt/bear_supply/uploads
sudo chown -R $USER:$USER /opt/bear_supply   # или нужный пользователь

# Создать .env (скопировать с другого места или задать вручную)
nano /opt/bear_supply/.env
```

В `.env` на сервере должны быть как минимум:

- `BEAR_SUPPLY_TOKEN` — токен Telegram-бота  
- `BEAR_SUPPLY_GROUP_ID` — ID группы (например `-5118688028`)  
- `BEAR_SUPPLY_SHEET_ID` — ID Google-таблицы  
- `BEAR_SUPPLY_TOKEN_JSON` — путь к `token.json` (например `/opt/bear_supply/creds/token.json`)  
- при необходимости: `BEAR_SUPPLY_DRIVE_FOLDER_ID`, `BEAR_SUPPLY_WORKSHEET_NAME`, `BEAR_SUPPLY_DOWNLOAD_DIR`

Файл **`/opt/bear_supply/creds/token.json`** нужно скопировать на сервер отдельно (полученный через OAuth, не коммитить в git). Токен должен быть выдан **с обоими областями доступа**: Drive и Google Sheets (скрипт `auth_drive.py` в репозитории запрашивает оба). Если при загрузке в Drive или записи в таблицу появляется `RefreshError: invalid_scope` — заново пройдите OAuth через `auth_drive.py` и замените `token.json` на сервере.

**Если при запуске ошибка** `Env BEAR_SUPPLY_SHEET_ID is not set` (или про другие переменные) — на сервере нет или не подгружен `.env`. Создайте `/opt/bear_supply/.env` с переменными (см. `.env.example` в репозитории) и перед запуском бота выполните: `set -a && source /opt/bear_supply/.env && set +a`.

### Запуск бота

**Активация окружения:** подгрузить `.env` и использовать Python из venv.

```bash
cd /opt/bear_supply

# Переменные из .env
set -a
source /opt/bear_supply/.env
set +a

# Запуск (python из venv)
/opt/bear_supply/venv/bin/python3 /opt/bear_supply/bear_supply_bot.py
```

Либо сначала активировать venv в текущей оболочке (в приглашении появится `(venv)`):

```bash
cd /opt/bear_supply
source /opt/bear_supply/venv/bin/activate
set -a && source /opt/bear_supply/.env && set +a
python3 bear_supply_bot.py
```

Для фонового запуска (systemd или screen/tmux):

```bash
# Пример через nohup
nohup /opt/bear_supply/venv/bin/python3 /opt/bear_supply/bear_supply_bot.py >> /opt/bear_supply/bot.log 2>&1 &
```

### Обновление кода с GitHub

После изменений в репозитории на сервере:

```bash
cd /opt/bear_supply
git pull origin main
```

Если менялись зависимости:

```bash
source venv/bin/activate
pip install -r requirements.txt
```

Перезагрузить переменные окружения (если обновлялся `.env`):

```bash
set -a && source .env && set +a
```

Перезапустить бота (systemd-сервис):

```bash
sudo systemctl restart bear_supply
sudo systemctl status bear_supply
```

Посмотреть логи:

```bash
journalctl -u bear_supply -f
```

---

## 3. Краткий чеклист

| Действие | Где |
|----------|-----|
| Код и документация | В git, пушим на GitHub |
| Секреты (токены, token.json) | Только на сервере: `.env` и `creds/token.json`, не в репозитории |
| Зависимости | `pip install -r requirements.txt` в venv на DO |
| Запуск | systemd-сервис `bear_supply` или `source .env` + `python3 bear_supply_bot.py` |

---

## 4. Systemd-сервис `bear_supply`

Чтобы бот автоматически запускался при старте сервера и перезапускался при сбоях, используется unit:

```ini
[Unit]
Description=Bear Supply Telegram Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/bear_supply
EnvironmentFile=/opt/bear_supply/.env
ExecStart=/opt/bear_supply/venv/bin/python /opt/bear_supply/bear_supply_bot.py
Restart=always
RestartSec=10

StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

Создание и включение:

```bash
sudo nano /etc/systemd/system/bear_supply.service   # вставить unit выше
sudo systemctl daemon-reload
sudo systemctl enable bear_supply
sudo systemctl start bear_supply
sudo systemctl status bear_supply
```

Быстрый перезапуск после обновления кода:

```bash
cd /opt/bear_supply
git pull origin main
sudo systemctl restart bear_supply
```

