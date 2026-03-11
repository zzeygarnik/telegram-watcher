import asyncio
import logging
import sys
import time
from pyrogram import Client
from pyrogram.errors import FloodWait

# Импорт конфига
from config import (
    API_ID, API_HASH, SOURCE_CHANNEL, TARGET_CHANNEL, HISTORY_DEPTH
)
import config 
from storage import Storage

# Логгер
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# Инициализация
app = Client("my_mirror_bot", api_id=API_ID, api_hash=API_HASH)
db = Storage(config)
ALBUM_CACHE = set()
msg_queue = asyncio.Queue()
last_activity = time.time()

# Настройки опроса (в секундах)
POLL_INTERVAL = 10
WATCHDOG_TIMEOUT = 300  # 5 минут без активности → перезапуск

# --- 0. WATCHDOG ---
async def watchdog_loop():
    logger.info("🐕 Watchdog started")
    while True:
        await asyncio.sleep(60)
        idle = time.time() - last_activity
        if idle > WATCHDOG_TIMEOUT:
            logger.critical(f"💀 Watchdog: no activity for {idle:.0f}s, forcing restart")
            sys.exit(1)

# --- 1. ВОРКЕР (Обработчик очереди - без изменений) ---
async def worker_loop(client, target_id):
    logger.info("👷 Worker started")
    while True:
        message = await msg_queue.get()
        try:
            chat_id = message.chat.id
            msg_id = message.id

            if await db.is_processed(chat_id, msg_id):
                msg_queue.task_done()
                continue

            # Альбомы
            if message.media_group_id:
                if message.media_group_id in ALBUM_CACHE:
                    msg_queue.task_done()
                    continue
                ALBUM_CACHE.add(message.media_group_id)
                logger.info(f"📚 Album detected: {message.media_group_id}")
                
                # Ждем, пока Telegram "обновит" данные о группе медиа
                await asyncio.sleep(2) 

                try:
                    # Запрашиваем полную группу медиа
                    media_group = await client.get_media_group(chat_id, msg_id)
                except ValueError:
                    media_group = [message]

                is_fwd = any(m.forward_date for m in media_group)
                if is_fwd:
                    await client.forward_messages(target_id, chat_id, [m.id for m in media_group])
                else:
                    await client.copy_media_group(target_id, chat_id, msg_id)

                for m in media_group: await db.mark_processed(chat_id, m.id)
                if len(ALBUM_CACHE) > 100: ALBUM_CACHE.clear()
                await db.log_event("SENT", message, "Album mirrored")

            # Обычные сообщения
            else:
                if message.forward_date:
                    await message.forward(target_id)
                else:
                    await message.copy(target_id)
                
                await db.mark_processed(chat_id, msg_id)
                logger.info(f"✅ Sent Msg {msg_id}")
                await db.log_event("SENT", message, "Message mirrored")

        except Exception as e:
            logger.error(f"❌ Worker Error: {e}")
            await db.log_event("ERROR", "System", str(e))
        finally:
            msg_queue.task_done()

# --- 2. ПОЛЛЕР (Активный опрос) ---
async def polling_loop(client, source_id):
    """
    Вместо ожидания уведомлений, мы сами проверяем канал каждые N секунд.
    Это работает, даже если PUSH-уведомления сломаны.
    """
    logger.info(f"🔄 Polling loop started for {source_id}")
    while True:
        try:
            # Берем последние 10 сообщений (на случай, если пришло несколько сразу)
            # reverse=True нужно, чтобы они шли от старых к новым
            messages = []
            async for m in client.get_chat_history(source_id, limit=10):
                messages.append(m)
            
            # Разворачиваем, чтобы обрабатывать в хронологическом порядке
            for message in reversed(messages):
                # Если сообщение УЖЕ в базе - игнорируем (молча)
                if await db.is_processed(message.chat.id, message.id):
                    continue
                
                # Если НОВОЕ - кидаем в очередь
                logger.info(f"📥 New message found via polling: {message.id}")
                await msg_queue.put(message)

            global last_activity
            last_activity = time.time()

        except FloodWait as e:
            logger.warning(f"⏳ FloodWait {e.value}s")
            await asyncio.sleep(e.value)
        except Exception as e:
            logger.error(f"⚠️ Polling error: {e}")
            # Не падаем, просто ждем следующего цикла

        # Спим перед следующим запросом
        await asyncio.sleep(POLL_INTERVAL)

async def resolve_chat(client, identifier):
    try:
        chat = await client.get_chat(identifier)
        return chat.id
    except:
        async for dialog in client.get_dialogs():
            if str(dialog.chat.id) == str(identifier): return dialog.chat.id
            if dialog.chat.username and str(dialog.chat.username).lower() == str(identifier).lower().replace("@", ""): return dialog.chat.id
    raise ValueError(f"Chat {identifier} not found")

# --- MAIN ---
async def main():
    await db.connect()
    logger.info("🚀 Bot Starting (Polling Mode) | v2 — watchdog + asyncpg timeouts")
    await app.start()

    try:
        source_id = await resolve_chat(app, SOURCE_CHANNEL)
        target_id = await resolve_chat(app, TARGET_CHANNEL)
        logger.info(f"🎯 Config: {source_id} -> {target_id}")
    except Exception as e:
        logger.error(f"Startup failed: {e}")
        await app.stop()
        return

    # Запускаем три параллельных процесса:
    # 1. Worker (отправляет сообщения)
    asyncio.create_task(worker_loop(app, target_id))
    # 2. Watchdog (перезапускает при зависании)
    asyncio.create_task(watchdog_loop())
    # 3. Poller (ищет новые сообщения)
    await polling_loop(app, source_id)

    # Сюда код дойдет только если polling_loop упадет (чего быть не должно)
    await app.stop()

if __name__ == "__main__":
    asyncio.run(main())