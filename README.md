# 📡 Telegram-Watcher

A self-hosted Telegram channel mirroring bot that silently copies posts from a source channel to a mirror channel — without revealing the original source. Built with Python, Pyrogram, PostgreSQL, and Docker.

---

## ✨ Features

- **Silent mirroring** — messages are copied (not forwarded), so no source attribution appears in the mirror channel
- **Smart forwarding** — if a post in the source channel is itself a forward from another user or channel, that attribution *is* preserved
- **Album support** — correctly handles media groups (e.g. 5 photos + caption) as a single cohesive post
- **All media types** — text, photos, videos, voice messages, video notes (circles), documents, audio, stickers
- **Live polling** — actively polls the source channel every N seconds, works even when Telegram push notifications fail
- **History backfill** — on first launch, mirrors existing messages up to a configurable depth
- **Duplicate protection** — PostgreSQL-backed deduplication prevents re-sending already mirrored messages
- **Web dashboard** — real-time activity log via Streamlit UI (auto-refreshes every 10 seconds)
- **Docker-ready** — fully containerized, designed to run on home servers (e.g. TrueNAS, Unraid)

---

## 🗂️ Project Structure

```
telegram-watcher/
├── main.py              # Bot core: polling loop + message worker
├── storage.py           # PostgreSQL async storage (asyncpg)
├── dashboard.py         # Streamlit monitoring dashboard
├── scan.py              # Utility: scan and print real channel IDs
├── reset_db.py          # Utility: manually remove specific message IDs from DB
├── create_session.py    # Utility: create or re-create the Telegram session file
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
# config.py

API_ID      = 123456           # From https://my.telegram.org
API_HASH    = "your_api_hash"
SOURCE_CHANNEL  = -1001234567890  # Source channel ID
TARGET_CHANNEL  = -1009876543210  # Mirror channel ID
HISTORY_DEPTH   = 100             # How many past messages to backfill

DB_HOST = "your_postgres_host"
DB_PORT = 5432
DB_NAME = "telegram_watcher"
DB_USER = "postgres"
DB_PASS = "your_password"
```

### 🌐 Proxy support (optional)

If Telegram is blocked in your region, set the `PROXY_URL` environment variable in your container settings:

```
PROXY_URL=socks5://user:pass@host:port
```

Both SOCKS5 and HTTP proxies are supported. If the variable is not set, the bot connects directly.

---

## 🚀 Getting Started

### Prerequisites

- Docker & Docker Compose
- A Telegram account (not a bot token — a user account session is required)
- PostgreSQL database (can be a separate container)

### 1. Get your Telegram session file

Run `create_session.py` locally to authenticate and generate the `my_mirror_bot.session` file:

```bash
pip install pyrogram==2.0.106 tgcrypto
python create_session.py
```

Follow the Pyrogram auth flow (enter your phone number and the code from Telegram). This creates `my_mirror_bot.session` in the project directory. Place it on your server alongside `config.py`.

### 2. Configure

```bash
cp config.example.py config.py
# Edit config.py with your values
```

Use `scan.py` to find the real numeric IDs of your source and target channels:

```bash
python scan.py
```

Send a message to the channel — the numeric ID will appear in the console output.

### 3. Run with Docker

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

Or with Docker Compose (recommended):

```bash
docker compose up -d
```

### 4. Access the Dashboard

Open [http://localhost:8501](http://localhost:8501) in your browser.

---

## 🖥️ Dashboard

The Streamlit dashboard shows a live activity log with color-coded event types:

| Color  | Event Type | Meaning                     |
|--------|------------|-----------------------------|
| 🔵 Blue  | RECEIVED   | Message picked up from source |
| 🟢 Green | SENT       | Message mirrored successfully |
| 🔴 Red   | ERROR      | Something went wrong         |
| 🟠 Orange | WARNING   | FloodWait or soft issue      |

All timestamps are displayed in **Moscow Time (UTC+3)**.

---

## 🛠️ Utility Scripts

### `create_session.py`
Creates or re-creates the `my_mirror_bot.session` file. Run this locally whenever the session becomes invalid (e.g. after being revoked via Telegram Settings → Devices).

```bash
python create_session.py
```

After `Session OK!` appears, copy `my_mirror_bot.session` to your server's app directory and restart the bot.

### `scan.py`
Listens for incoming messages and prints the **real numeric chat ID** of any channel that sends a message. Use this to find `SOURCE_CHANNEL` and `TARGET_CHANNEL` values.

```bash
python scan.py
```

### `reset_db.py`
Removes specific message IDs from the `posted_messages` table, forcing the bot to re-mirror them on the next poll cycle. Edit the `TARGET_IDS` list inside the script before running.

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
| Hosting       | TrueNAS / any Linux server          |

---

## 🔒 Security Notes

- Never commit `config.py` or `.session` files to version control
- Add both to `.gitignore` before your first commit
- The `.session` file grants full access to your Telegram account
- Consider using environment variables or a `.env` file for production deployments

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
- **Поддержка альбомов** — корректно обрабатывает медиагруппы (например, 5 фото + подпись) как единое сообщение
- **Все типы медиа** — текст, фото, видео, голосовые, кружочки, документы, музыка, стикеры
- **Активный поллинг** — бот сам опрашивает канал каждые N секунд, работает даже если Telegram не присылает push-уведомления
- **Заполнение истории** — при первом запуске зеркалирует уже существующие сообщения на заданную глубину
- **Защита от дублей** — PostgreSQL хранит ID обработанных сообщений, повторная отправка исключена
- **Веб-дашборд** — лог активности в реальном времени через Streamlit (обновляется каждые 10 секунд)
- **Docker-ready** — полностью контейнеризирован, рассчитан на запуск на домашнем сервере (TrueNAS, Unraid и др.)

---

## 🗂️ Структура проекта

```
telegram-watcher/
├── main.py              # Ядро бота: цикл поллинга + воркер сообщений
├── storage.py           # Асинхронное хранилище PostgreSQL (asyncpg)
├── dashboard.py         # Дашборд мониторинга на Streamlit
├── scan.py              # Утилита: поиск реального числового ID канала
├── reset_db.py          # Утилита: удаление конкретных сообщений из БД
├── create_session.py    # Утилита: создание или пересоздание файла сессии Telegram
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
# config.py

API_ID      = 123456           # С https://my.telegram.org
API_HASH    = "твой_api_hash"
SOURCE_CHANNEL  = -1001234567890  # ID канала-источника
TARGET_CHANNEL  = -1009876543210  # ID канала-зеркала
HISTORY_DEPTH   = 100             # Глубина заполнения истории (кол-во сообщений)

DB_HOST = "адрес_твоей_бд"
DB_PORT = 5432
DB_NAME = "telegram_watcher"
DB_USER = "postgres"
DB_PASS = "твой_пароль"
```

### 🌐 Поддержка прокси (опционально)

Если Telegram заблокирован в твоём регионе, задай переменную окружения `PROXY_URL` в настройках контейнера:

```
PROXY_URL=socks5://user:pass@host:port
```

Поддерживаются SOCKS5 и HTTP прокси. Если переменная не задана — бот подключается напрямую.

---

## 🚀 Быстрый старт

### Что нужно заранее

- Docker и Docker Compose
- Аккаунт Telegram (не бот-токен — требуется сессия пользовательского аккаунта)
- База данных PostgreSQL (может быть отдельным контейнером)

### 1. Получи файл сессии Telegram

Запусти `create_session.py` локально, чтобы пройти авторизацию и создать файл `my_mirror_bot.session`:

```bash
pip install pyrogram==2.0.106 tgcrypto
python create_session.py
```

Следуй инструкциям: введи номер телефона и код из Telegram. После появления `Session OK!` файл `my_mirror_bot.session` будет создан в папке проекта. Скопируй его на сервер рядом с `config.py`.

### 2. Настройка

```bash
cp config.example.py config.py
# Отредактируй config.py, вписав свои значения
```

Используй `scan.py`, чтобы найти реальные числовые ID каналов:

```bash
python scan.py
```

Напиши что-нибудь в канал — числовой ID появится в выводе консоли.

### 3. Запуск через Docker

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

Или через Docker Compose (рекомендуется):

```bash
docker compose up -d
```

### 4. Открой дашборд

Перейди в браузере по адресу [http://localhost:8501](http://localhost:8501).

---

## 🖥️ Дашборд

Streamlit-дашборд показывает лог активности с цветовой индикацией событий:

| Цвет     | Тип события | Значение                          |
|----------|-------------|-----------------------------------|
| 🔵 Синий  | RECEIVED    | Сообщение получено из источника   |
| 🟢 Зелёный | SENT       | Сообщение успешно зеркалировано   |
| 🔴 Красный | ERROR      | Произошла ошибка                  |
| 🟠 Оранжевый | WARNING  | FloodWait или мягкая проблема     |

Все временные метки отображаются по **московскому времени (UTC+3)**.

---

## 🛠️ Утилиты

### `create_session.py`
Создаёт или пересоздаёт файл `my_mirror_bot.session`. Запускай локально, когда сессия становится невалидной (например, после отзыва через Telegram → Настройки → Устройства).

```bash
python create_session.py
```

После появления `Session OK!` скопируй `my_mirror_bot.session` в папку приложения на сервере и перезапусти бота.

### `scan.py`
Слушает входящие сообщения и выводит **реальный числовой ID** любого канала, который пришлёт сообщение. Используй для определения `SOURCE_CHANNEL` и `TARGET_CHANNEL`.

```bash
python scan.py
```

### `reset_db.py`
Удаляет конкретные ID сообщений из таблицы `posted_messages`, заставляя бота повторно зеркалировать их на следующем цикле опроса. Перед запуском отредактируй список `TARGET_IDS` внутри скрипта.

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
| Хостинг         | TrueNAS / любой Linux-сервер            |

---

## 🔒 Безопасность

- Никогда не коммить `config.py` и `.session` файлы в репозиторий
- Оба файла уже добавлены в `.gitignore`
- Файл `.session` даёт полный доступ к твоему аккаунту Telegram
- Для продакшена рекомендуется перейти на переменные окружения или `.env` файл

---

## 📄 Лицензия

MIT License. Используй на свой страх и риск. Зеркалирование каналов может нарушать Условия использования Telegram в зависимости от контента и контекста.
