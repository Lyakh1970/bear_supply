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

# Каталоги для секретов и загрузок
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

Файл **`/opt/bear_supply/creds/token.json`** нужно скопировать на сервер отдельно (полученный через OAuth, не коммитить в git).

### Запуск бота

```bash
cd /opt/bear_supply
set -a
source /opt/bear_supply/.env
set +a
/opt/bear_supply/venv/bin/python3 /opt/bear_supply/bear_supply_bot.py
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
# Перезапустить бота
```

---

## 3. Краткий чеклист

| Действие | Где |
|----------|-----|
| Код и документация | В git, пушим на GitHub |
| Секреты (токены, token.json) | Только на сервере: `.env` и `creds/token.json`, не в репозитории |
| Зависимости | `pip install -r requirements.txt` в venv на DO |
| Запуск | `source .env` + `python3 bear_supply_bot.py` |
