import asyncpg
import logging
from datetime import datetime
import pytz

logger = logging.getLogger(__name__)

class Storage:
    def __init__(self, config):
        self.config = config
        self.pool = None
        self.moscow_tz = pytz.timezone('Europe/Moscow')

    async def connect(self):
        """Инициализация пула соединений и таблиц."""
        self.pool = await asyncpg.create_pool(
            host=self.config.DB_HOST,
            port=self.config.DB_PORT,
            user=self.config.DB_USER,
            password=self.config.DB_PASS,
            database=self.config.DB_NAME,
            min_size=5,
            max_size=20,
            command_timeout=30,
            max_inactive_connection_lifetime=60,
        )
        async with self.pool.acquire() as conn:
            # Таблица сообщений
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS posted_messages (
                    chat_id BIGINT,
                    msg_id INTEGER,
                    posted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (chat_id, msg_id)
                );
            """)
            # Таблица логов
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS bot_logs (
                    id SERIAL PRIMARY KEY,
                    event_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    event_type VARCHAR(20),
                    message_type VARCHAR(20),
                    description TEXT
                );
            """)
        logger.info("Database storage initialized (async).")

    async def is_processed(self, chat_id: int, msg_id: int) -> bool:
        async with self.pool.acquire() as conn:
            res = await conn.fetchval(
                "SELECT 1 FROM posted_messages WHERE chat_id = $1 AND msg_id = $2",
                chat_id, msg_id
            )
            return res is not None

    async def get_max_processed_id(self, chat_id: int) -> int:
        async with self.pool.acquire() as conn:
            res = await conn.fetchval(
                "SELECT MAX(msg_id) FROM posted_messages WHERE chat_id = $1",
                chat_id
            )
            return res or 0

    async def mark_processed(self, chat_id: int, msg_id: int):
        async with self.pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO posted_messages (chat_id, msg_id) VALUES ($1, $2) ON CONFLICT DO NOTHING",
                chat_id, msg_id
            )

    async def log_event(self, event_type: str, message, description: str):
        """Логирование события в БД с улучшенным определением типов."""
        msg_type = "System"
        
        # Если это объект сообщения Pyrogram
        if hasattr(message, "id"):
            if message.media_group_id: 
                msg_type = "Album"
            elif message.photo: 
                msg_type = "Photo"
            elif message.video: 
                msg_type = "Video"
            elif message.voice:       # <--- Добавили Голосовые
                msg_type = "Voice"
            elif message.video_note:  # <--- Добавили "Кружочки"
                msg_type = "Round Video"
            elif message.document:    # <--- Добавили Файлы
                msg_type = "File"
            elif message.audio:       # <--- Добавили Музыку
                msg_type = "Audio"
            elif message.sticker:     # <--- Добавили Стикеры
                msg_type = "Sticker"
            elif message.text: 
                msg_type = "Text"
            else:
                msg_type = "Other"

        async with self.pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO bot_logs (event_type, message_type, description) VALUES ($1, $2, $3)",
                event_type, msg_type, description
            )