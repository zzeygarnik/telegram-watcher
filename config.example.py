# =============================================================================
# config.example.py — Copy this file to config.py and fill in your values.
# DO NOT commit config.py to version control.
# =============================================================================

# --- Telegram API credentials ---
# Get these from https://my.telegram.org → API Development Tools
API_ID   = 0              # Integer
API_HASH = "your_api_hash_here"

# --- Channel IDs ---
# Use scan.py to find the real numeric IDs of your channels
SOURCE_CHANNEL = -1001234567890   # Channel to mirror FROM
TARGET_CHANNEL = -1009876543210   # Channel to mirror TO

# --- Bot behavior ---
HISTORY_DEPTH = 100   # Number of past messages to backfill on first launch
SEND_DELAY = 0

# --- PostgreSQL ---
DB_HOST = "localhost"
DB_PORT = 5432
DB_NAME = "telegram_watcher"
DB_USER = "postgres"
DB_PASS = "your_password_here"

# --- Proxy (optional) ---
# If Telegram is blocked in your region, set the PROXY_URL environment variable
# in your container settings. Format: socks5://user:pass@host:port
# Both SOCKS5 and HTTP are supported. Leave unset to connect directly.
# This is read automatically from the environment — no changes needed here.
