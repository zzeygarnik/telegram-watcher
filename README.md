# 📡 Telegram-Watcher

A self-hosted Telegram channel mirroring bot that silently copies posts from a source channel to a mirror channel — without revealing the original source. Built with Python, Pyrogram, PostgreSQL, and Docker.

---

## ✨ Features

- **Silent mirroring** — messages are copied (not forwarded), so no source attribution appears in the mirror channel
- **Smart forwarding** — if a post in the source channel is itself a forward from another user or channel, that attribution *is* preserved
- **Real-time events** — uses Pyrogram's MTProto event system to receive messages instantly as they arrive, no polling delay
- **Startup catchup** — on every launch, checks the last `HISTORY_DEPTH` messages and queues any that were missed during downtime
- **Smart album sync** — dynamically polls `get_media_group` until the part count stabilizes (two equal consecutive checks), then forwards — no fixed delay, no partial albums
- **All media types** — text, photos, videos, voice messages, video notes (circles), documents, audio, stickers
- **Duplicate protection** — PostgreSQL-backed deduplication prevents re-sending already mirrored messages
- **Watchdog** — automatically restarts the worker if it crashes silently
- **Service message handling** — service events (pins, channel creation, etc.) are logged and skipped cleanly without errors
- **Web dashboard** — real-time activity log via Streamlit UI (auto-refreshes every 10 seconds)
- **Docker-ready** — fully containerized, designed to run on any Linux server

---

## 🗂️ Project Structure

```
telegram-watcher/
├── main.py              # Bot core: event handler, worker queue, watchdog, startup catchup
├── storage.py           # PostgreSQL async storage (asyncpg)
├── dashboard.py         # Streamlit monitoring dashboard
├── scan.py              # Utility: scan and print real channel IDs
├── reset_db.py          # Utility: manually remove specific message IDs from DB
├── config.example.py    # Configuration template (copy to config.py and fill in)
├── requirements.txt     # Python dependencies
├── Dockerfile           # Container image definition
├── start.sh             # Entrypoint: starts dashboard + bot
└── .gitignore
```

> ⚠️ `config.py` and `*.session` files are **not** included in the repository and must never be committed.

---

## ⚙️ Configuration

Copy `config.example.py` to `config.py` and fill in your values:

```python
API_ID      = 123456
API_HASH    = "your_api_hash"
SOURCE_CHANNEL  = -1001234567890  # Source channel ID
TARGET_CHANNEL  = -1009876543210  # Mirror channel ID
HISTORY_DEPTH   = 100             # How many recent messages to check for catchup on startup

# If PostgreSQL runs on the host: use "localhost"
# If PostgreSQL runs in a Docker container on the same network: use the container name
DB_HOST = "localhost"
DB_PORT = 5432
DB_NAME = "telegram_watcher"
DB_USER = "postgres"
DB_PASS = "your_password"

PROXY = None  # or {"scheme": "socks5", "hostname": "host", "port": 1234}
```

### 🌐 Proxy support (optional)

If Telegram is blocked in your region, set `PROXY` in `config.py`:

```python
PROXY = {"scheme": "socks5", "hostname": "your.proxy.host", "port": 1234}
# With authentication:
PROXY = {"scheme": "socks5", "hostname": "your.proxy.host", "port": 1234, "username": "user", "password": "pass"}
```

Both SOCKS5 and HTTP proxies are supported. Set `PROXY = None` to connect directly.

---

## 🚀 Getting Started

### Prerequisites

- Docker
- A Telegram account (not a bot token — a user account session is required)
- PostgreSQL database (can run directly on the host or in a Docker container)

### 1. Get your Telegram session file

Run `scan.py` locally to authenticate and generate the session file:

```bash
pip install pyrogram tgcrypto
python scan.py
```

This creates `scanner_session.session`. To generate `my_mirror_bot.session` (the name the bot expects) directly, run:

```bash
python -c "from pyrogram import Client; from config import API_ID, API_HASH; Client('my_mirror_bot', api_id=API_ID, api_hash=API_HASH).run()"
```

Follow the Pyrogram auth flow (phone number + code from Telegram). Once done, press `Ctrl+C`.

### 2. Configure

```bash
cp config.example.py config.py
# Edit config.py with your values
```

Use `scan.py` to find the real numeric IDs of your channels — send a message to a channel and the ID will appear in the console output.

### 3. Set up the database

Create the database and user in PostgreSQL:

```sql
CREATE DATABASE telegram_watcher;
CREATE USER tg_mirror WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE telegram_watcher TO tg_mirror;
ALTER DATABASE telegram_watcher OWNER TO tg_mirror;
```

**If PostgreSQL runs in Docker**, execute via the container:

```bash
docker exec -it <postgres_container_name> psql -U postgres -c "CREATE DATABASE telegram_watcher;"
docker exec -it <postgres_container_name> psql -U postgres -c "CREATE USER tg_mirror WITH PASSWORD 'your_password';"
docker exec -it <postgres_container_name> psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE telegram_watcher TO tg_mirror;"
docker exec -it <postgres_container_name> psql -U postgres -c "ALTER DATABASE telegram_watcher OWNER TO tg_mirror;"
```

Then set `DB_HOST` in `config.py` to the **container name** (not `localhost`), and make sure both containers are on the same Docker network (see step 4).

### 4. Run with Docker

**Simple setup** (PostgreSQL on host):

```bash
docker build -t telegram-watcher .
docker run -d \
  --name telegram-watcher \
  --restart unless-stopped \
  -p 8501:8501 \
  -v $(pwd)/config.py:/app/config.py \
  -v $(pwd)/my_mirror_bot.session:/app/my_mirror_bot.session \
  telegram-watcher
```

**PostgreSQL also in Docker** — both containers must share a network:

```bash
docker network create tg-net
docker network connect tg-net <postgres_container_name>

docker run -d \
  --name telegram-watcher \
  --restart unless-stopped \
  --network tg-net \
  -p 8501:8501 \
  -v $(pwd)/config.py:/app/config.py \
  -v $(pwd)/my_mirror_bot.session:/app/my_mirror_bot.session \
  telegram-watcher
```

### 5. Access the Dashboard

Open [http://localhost:8501](http://localhost:8501) in your browser.

---

## 🔄 Redeploying after code changes

```bash
git pull
docker build -t telegram-watcher .
docker rm -f telegram-watcher
docker run -d --name telegram-watcher --restart unless-stopped --network tg-net \
  -p 8501:8501 \
  -v $(pwd)/config.py:/app/config.py \
  -v $(pwd)/my_mirror_bot.session:/app/my_mirror_bot.session \
  telegram-watcher
```

---

## 🖥️ Dashboard

The Streamlit dashboard shows a live activity log with color-coded event types:

| Color  | Event Type | Meaning                     |
|--------|------------|-----------------------------|
| 🟢 Green | SENT       | Message mirrored successfully |
| 🔴 Red   | ERROR      | Something went wrong         |
| 🟠 Orange | WARNING   | FloodWait or soft issue      |

All timestamps are displayed in **Moscow Time (UTC+3)**.

---

## 🛠️ Utility Scripts

### `scan.py`
Listens for incoming messages and prints the **real numeric chat ID** of any channel that sends a message. Use this to find `SOURCE_CHANNEL` and `TARGET_CHANNEL` values.

```bash
python scan.py
```

### `reset_db.py`
Removes specific message IDs from the `posted_messages` table, forcing the bot to re-mirror them on the next startup catchup. Edit the `TARGET_IDS` list inside the script before running.

```bash
python reset_db.py
```

---

## 📦 Tech Stack

| Component     | Technology                          |
|---------------|-------------------------------------|
| Bot framework | [Pyrogram](https://pyrogram.org/) 2.x |
| Database      | PostgreSQL via [asyncpg](https://github.com/MagicStack/asyncpg) |
| Dashboard     | [Streamlit](https://streamlit.io/)  |
| Containerization | Docker                           |
| Hosting       | Any Linux server                    |

---

## 🔒 Security Notes

- Never commit `config.py` or `.session` files to version control
- Both are already covered by `.gitignore`
- The `.session` file grants full access to your Telegram account

---

## 📄 License

MIT License. Use at your own risk. Mirroring channels may violate Telegram's Terms of Service depending on the content and context.

---
---

# 📡 Telegram-Watcher (на русском)

Самохостируемый бот для зеркалирования Telegram-каналов. Копирует посты из канала-источника в канал-зеркало без указания источника. Написан на Python с использованием Pyrogram, PostgreSQL и Docker.

---

## ✨ Возможности

- **Тихое зеркалирование** — сообщения копируются, а не пересылаются, поэтому в канале-зеркале не отображается источник
- **Умная пересылка** — если пост в канале-источнике сам является пересылкой от другого пользователя или канала, авторство сохраняется
- **События в реальном времени** — использует MTProto-механизм Pyrogram: сообщения приходят мгновенно, без polling-задержки
- **Catchup при запуске** — при каждом старте бот проверяет последние `HISTORY_DEPTH` сообщений и ставит в очередь всё, что пропустил во время простоя
- **Умная синхронизация альбомов** — динамически опрашивает `get_media_group` пока количество частей не стабилизируется (два одинаковых результата подряд), только потом пересылает — никаких фиксированных задержек и неполных альбомов
- **Все типы медиа** — текст, фото, видео, голосовые, кружочки, документы, музыка, стикеры
- **Защита от дублей** — PostgreSQL хранит ID обработанных сообщений, повторная отправка исключена
- **Watchdog** — автоматически перезапускает воркер при тихом сбое
- **Обработка сервисных сообщений** — события типа «закреп», «создание канала» и т.д. логируются и пропускаются без ошибок
- **Веб-дашборд** — лог активности в реальном времени через Streamlit (обновляется каждые 10 секунд)
- **Docker-ready** — полностью контейнеризирован, рассчитан на запуск на любом Linux-сервере

---

## 🗂️ Структура проекта

```
telegram-watcher/
├── main.py              # Ядро бота: event handler, очередь воркера, watchdog, catchup при старте
├── storage.py           # Асинхронное хранилище PostgreSQL (asyncpg)
├── dashboard.py         # Дашборд мониторинга на Streamlit
├── scan.py              # Утилита: поиск реального числового ID канала
├── reset_db.py          # Утилита: удаление конкретных сообщений из БД
├── config.example.py    # Шаблон конфигурации (скопируй в config.py и заполни)
├── requirements.txt     # Python-зависимости
├── Dockerfile           # Образ контейнера
├── start.sh             # Точка входа: запускает дашборд и бота
└── .gitignore
```

> ⚠️ Файлы `config.py` и `*.session` **не включены** в репозиторий и никогда не должны туда попадать.

---

## ⚙️ Конфигурация

Скопируй `config.example.py` в `config.py` и заполни своими значениями:

```python
API_ID      = 123456
API_HASH    = "твой_api_hash"
SOURCE_CHANNEL  = -1001234567890  # ID канала-источника
TARGET_CHANNEL  = -1009876543210  # ID канала-зеркала
HISTORY_DEPTH   = 100             # Сколько последних сообщений проверять при catchup на старте

# Если PostgreSQL запущен на хосте — используй "localhost"
# Если PostgreSQL запущен в Docker-контейнере в той же сети — используй имя контейнера
DB_HOST = "localhost"
DB_PORT = 5432
DB_NAME = "telegram_watcher"
DB_USER = "postgres"
DB_PASS = "твой_пароль"

PROXY = None  # или {"scheme": "socks5", "hostname": "host", "port": 1234}
```

### 🌐 Поддержка прокси (опционально)

Если Telegram заблокирован в твоём регионе, задай `PROXY` в `config.py`:

```python
PROXY = {"scheme": "socks5", "hostname": "твой.прокси.хост", "port": 1234}
# С авторизацией:
PROXY = {"scheme": "socks5", "hostname": "твой.прокси.хост", "port": 1234, "username": "user", "password": "pass"}
```

Поддерживаются SOCKS5 и HTTP прокси. Чтобы подключаться напрямую — оставь `PROXY = None`.

---

## 🚀 Быстрый старт

### Что нужно заранее

- Docker
- Аккаунт Telegram (не бот-токен — требуется сессия пользовательского аккаунта)
- База данных PostgreSQL (может быть на хосте или в отдельном Docker-контейнере)

### 1. Получи файл сессии Telegram

Запусти `scan.py` локально, чтобы пройти авторизацию:

```bash
pip install pyrogram tgcrypto
python scan.py
```

Чтобы сразу создать файл с нужным именем (`my_mirror_bot.session`), выполни:

```bash
python -c "from pyrogram import Client; from config import API_ID, API_HASH; Client('my_mirror_bot', api_id=API_ID, api_hash=API_HASH).run()"
```

Введи номер телефона и код из Telegram. После успешного входа нажми `Ctrl+C`.

### 2. Настройка

```bash
cp config.example.py config.py
# Отредактируй config.py, вписав свои значения
```

Используй `scan.py`, чтобы найти реальные числовые ID каналов — напиши что-нибудь в канал и ID появится в выводе консоли.

### 3. Создай базу данных

Выполни в PostgreSQL:

```sql
CREATE DATABASE telegram_watcher;
CREATE USER tg_mirror WITH PASSWORD 'твой_пароль';
GRANT ALL PRIVILEGES ON DATABASE telegram_watcher TO tg_mirror;
ALTER DATABASE telegram_watcher OWNER TO tg_mirror;
```

**Если PostgreSQL запущен в Docker**, выполни через контейнер:

```bash
docker exec -it <имя_контейнера_postgres> psql -U postgres -c "CREATE DATABASE telegram_watcher;"
docker exec -it <имя_контейнера_postgres> psql -U postgres -c "CREATE USER tg_mirror WITH PASSWORD 'твой_пароль';"
docker exec -it <имя_контейнера_postgres> psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE telegram_watcher TO tg_mirror;"
docker exec -it <имя_контейнера_postgres> psql -U postgres -c "ALTER DATABASE telegram_watcher OWNER TO tg_mirror;"
```

Затем укажи в `config.py` значение `DB_HOST` равное **имени контейнера** (не `localhost`) и убедись, что оба контейнера находятся в одной Docker-сети (см. шаг 4).

### 4. Запуск через Docker

**Простой вариант** (PostgreSQL на хосте):

```bash
docker build -t telegram-watcher .
docker run -d \
  --name telegram-watcher \
  --restart unless-stopped \
  -p 8501:8501 \
  -v $(pwd)/config.py:/app/config.py \
  -v $(pwd)/my_mirror_bot.session:/app/my_mirror_bot.session \
  telegram-watcher
```

**PostgreSQL тоже в Docker** — оба контейнера должны быть в одной сети:

```bash
docker network create tg-net
docker network connect tg-net <имя_контейнера_postgres>

docker run -d \
  --name telegram-watcher \
  --restart unless-stopped \
  --network tg-net \
  -p 8501:8501 \
  -v $(pwd)/config.py:/app/config.py \
  -v $(pwd)/my_mirror_bot.session:/app/my_mirror_bot.session \
  telegram-watcher
```

### 5. Открой дашборд

Перейди в браузере по адресу [http://localhost:8501](http://localhost:8501).

---

## 🔄 Передеплой после изменений в коде

```bash
git pull
docker build -t telegram-watcher .
docker rm -f telegram-watcher
docker run -d --name telegram-watcher --restart unless-stopped --network tg-net \
  -p 8501:8501 \
  -v $(pwd)/config.py:/app/config.py \
  -v $(pwd)/my_mirror_bot.session:/app/my_mirror_bot.session \
  telegram-watcher
```

---

## 🖥️ Дашборд

Streamlit-дашборд показывает лог активности с цветовой индикацией событий:

| Цвет       | Тип события | Значение                        |
|------------|-------------|---------------------------------|
| 🟢 Зелёный  | SENT        | Сообщение успешно зеркалировано |
| 🔴 Красный  | ERROR       | Произошла ошибка                |
| 🟠 Оранжевый | WARNING    | FloodWait или мягкая проблема   |

Все временные метки отображаются по **московскому времени (UTC+3)**.

---

## 🛠️ Утилиты

### `scan.py`
Слушает входящие сообщения и выводит **реальный числовой ID** любого канала, который пришлёт сообщение. Используй для определения `SOURCE_CHANNEL` и `TARGET_CHANNEL`.

```bash
python scan.py
```

### `reset_db.py`
Удаляет конкретные ID сообщений из таблицы `posted_messages`, заставляя бота повторно зеркалировать их при следующем catchup на старте. Перед запуском отредактируй список `TARGET_IDS` внутри скрипта.

```bash
python reset_db.py
```

---

## 📦 Технологии

| Компонент       | Технология                              |
|-----------------|-----------------------------------------|
| Фреймворк бота  | [Pyrogram](https://pyrogram.org/) 2.x   |
| База данных     | PostgreSQL через [asyncpg](https://github.com/MagicStack/asyncpg) |
| Дашборд         | [Streamlit](https://streamlit.io/)      |
| Контейнеризация | Docker                                  |
| Хостинг         | Любой Linux-сервер                      |

---

## 🔒 Безопасность

- Никогда не коммить `config.py` и `.session` файлы в репозиторий
- Оба файла уже добавлены в `.gitignore`
- Файл `.session` даёт полный доступ к твоему аккаунту Telegram

---

## 📄 Лицензия

MIT License. Используй на свой страх и риск. Зеркалирование каналов может нарушать Условия использования Telegram в зависимости от контента и контекста.
