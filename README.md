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

---

## 🚀 Getting Started

### Prerequisites

- Docker & Docker Compose
- A Telegram account (not a bot token — a user account session is required)
- PostgreSQL database (can be a separate container)

### 1. Get your Telegram session file

Run `scan.py` locally first to authenticate and generate a `.session` file:

```bash
pip install pyrogram tgcrypto
python scan.py
```

Follow the Pyrogram auth flow. This creates `scanner_session.session` (or `my_mirror_bot.session` for the main bot). Place it in the project directory.

Use `scan.py` to find the real numeric IDs of your source and target channels by sending a message to them and reading the output.

### 2. Configure

```bash
cp config.example.py config.py
# Edit config.py with your values
```

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
