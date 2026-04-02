import asyncio
import logging
import sys
from pyrogram import Client, filters, idle
from pyrogram.handlers import MessageHandler

from config import (
    API_ID, API_HASH, SOURCE_CHANNEL, TARGET_CHANNEL, HISTORY_DEPTH, PROXY
)
import config
from storage import Storage

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)
logging.getLogger("pyrogram").setLevel(logging.WARNING)

app = Client("my_mirror_bot", api_id=API_ID, api_hash=API_HASH, proxy=PROXY)
if PROXY:
    logger.info(f"🌐 Proxy: {PROXY['scheme']}://{PROXY['hostname']}:{PROXY['port']}")
db = Storage(config)
ALBUM_CACHE = set()
msg_queue = None

API_TIMEOUT = 30
ALBUM_MAX_WAIT = 10.0      # максимум секунд ждать альбом
ALBUM_POLL_INTERVAL = 0.5  # как часто проверять get_media_group
KEEPALIVE_INTERVAL = 300   # пинг каждые 5 минут
CATCHUP_INTERVAL = 300     # полный catchup как страховка раз в 5 минут
FAST_POLL_INTERVAL = 5     # быстрый опрос на новые сообщения каждые 5 секунд
worker_task = None
_target_id = None
_source_id = None
_last_polled_id = 0        # последний ID, зафиксированный fast_poll


# --- 0. KEEPALIVE ---
async def keepalive_loop():
    """Пингует Telegram каждые KEEPALIVE_INTERVAL секунд.
    При silent disconnect — переподключается и делает catchup."""
    global _source_id
    logger.info("💓 Keepalive started")
    while True:
        await asyncio.sleep(KEEPALIVE_INTERVAL)
        try:
            await asyncio.wait_for(app.get_me(), timeout=20)
        except Exception as e:
            logger.error(f"💓 Keepalive ping failed ({e}), reconnecting...")
            for attempt in range(5):
                try:
                    try:
                        await app.stop()
                    except Exception:
                        pass
                    await asyncio.sleep(5 * (attempt + 1))
                    await app.start()
                    logger.info("💓 Reconnected to Telegram")
                    await catchup(app, _source_id)
                    break
                except Exception as re:
                    logger.error(f"💓 Reconnect attempt {attempt + 1}/5 failed: {re}")
            else:
                logger.critical("💓 All reconnect attempts failed — manual intervention needed")


# --- 0. FAST POLL ---
async def fast_poll_loop():
    """Опрашивает канал каждые FAST_POLL_INTERVAL секунд.
    Берёт 1 сообщение (дешёво), сравнивает ID с последним известным.
    Если есть новые — забирает только дельту и ставит в очередь."""
    global _source_id, _last_polled_id
    logger.info("⚡ Fast poll started")
    while True:
        await asyncio.sleep(FAST_POLL_INTERVAL)
        try:
            # Один дешёвый запрос — узнаём последний ID
            latest = None
            async for m in app.get_chat_history(_source_id, limit=1):
                latest = m
                break

            if latest is None:
                continue

            latest_id = latest.id

            if _last_polled_id == 0:
                _last_polled_id = latest_id
                continue

            if latest_id <= _last_polled_id:
                continue

            # Есть новые сообщения — забираем дельту
            gap = latest_id - _last_polled_id
            fetch_limit = min(gap + 5, 50)

            new_messages = []
            async for m in app.get_chat_history(_source_id, limit=fetch_limit):
                if m.id <= _last_polled_id:
                    break
                new_messages.append(m)

            queued = 0
            for m in reversed(new_messages):
                if not await db.is_processed(m.chat.id, m.id):
                    await msg_queue.put(m)
                    queued += 1

            if queued:
                logger.info(f"⚡ Fast poll: queued {queued} new messages up to id={latest_id}")

            _last_polled_id = latest_id

        except Exception as e:
            logger.error(f"⚡ Fast poll error: {e}")


# --- 0. PERIODIC CATCHUP ---
async def periodic_catchup_loop():
    """Страховка на случай silent MTProto disconnect: каждые CATCHUP_INTERVAL секунд
    догоняет пропущенные сообщения через прямые API-запросы."""
    global _source_id
    await asyncio.sleep(CATCHUP_INTERVAL)  # первый запуск после старта — дать время на нормальную работу
    while True:
        try:
            await catchup(app, _source_id)
        except Exception as e:
            logger.error(f"🔄 Periodic catchup error: {e}")
        await asyncio.sleep(CATCHUP_INTERVAL)


# --- 0. WATCHDOG ---
async def watchdog_loop():
    global worker_task, _target_id
    logger.info("🐕 Watchdog started")
    while True:
        await asyncio.sleep(60)
        if worker_task is not None and worker_task.done():
            exc = None
            if not worker_task.cancelled():
                try:
                    exc = worker_task.exception()
                except Exception:
                    pass
            logger.critical(f"💀 Watchdog: worker died (exc={exc}), restarting")
            worker_task = asyncio.create_task(worker_loop(app, _target_id))


# --- 1. ALBUM COLLECTOR ---
async def collect_album(client, chat_id, msg_id):
    """
    Опрашивает get_media_group с интервалом ALBUM_POLL_INTERVAL.
    Возвращает группу как только два последовательных вызова
    вернули одинаковое количество частей (альбом стабилен).
    Жёсткий таймаут — ALBUM_MAX_WAIT секунд.
    """
    prev_count = 0
    elapsed = 0.0

    while elapsed < ALBUM_MAX_WAIT:
        await asyncio.sleep(ALBUM_POLL_INTERVAL)
        elapsed += ALBUM_POLL_INTERVAL

        try:
            group = await asyncio.wait_for(
                client.get_media_group(chat_id, msg_id), timeout=5
            )
        except (ValueError, asyncio.TimeoutError):
            break

        if len(group) == prev_count and prev_count > 0:
            logger.info(f"📚 Album {msg_id} complete: {len(group)} parts in {elapsed:.1f}s")
            return group

        prev_count = len(group)

    # Таймаут — берём что есть
    logger.warning(f"⚠️ Album {msg_id} timed out after {elapsed:.1f}s, forwarding {prev_count} parts")
    try:
        return await asyncio.wait_for(client.get_media_group(chat_id, msg_id), timeout=5)
    except (ValueError, asyncio.TimeoutError):
        return None


# --- 2. HANDLERS ---
async def on_new_message(client, message):
    logger.info(f"📥 New message: {message.id}")
    await msg_queue.put(message)


async def on_service_message(client, message):
    logger.info(f"ℹ️ Service event in {message.chat.id} (id={message.id}, service={message.service}), skipping")


# --- 3. ВОРКЕР ---
async def worker_loop(client, target_id):
    logger.info("👷 Worker started")
    while True:
        message = await msg_queue.get()
        msg_id = None
        try:
            chat_id = message.chat.id
            msg_id = message.id

            if await db.is_processed(chat_id, msg_id):
                continue

            # Альбомы
            if message.media_group_id:
                if message.media_group_id in ALBUM_CACHE:
                    continue
                ALBUM_CACHE.add(message.media_group_id)
                logger.info(f"📚 Album detected: {message.media_group_id}")

                media_group = await collect_album(client, chat_id, msg_id)
                if media_group is None:
                    media_group = [message]

                is_fwd = any(m.forward_date for m in media_group)
                if is_fwd:
                    await asyncio.wait_for(
                        client.forward_messages(target_id, chat_id, [m.id for m in media_group]),
                        timeout=API_TIMEOUT
                    )
                else:
                    await asyncio.wait_for(
                        client.copy_media_group(target_id, chat_id, msg_id),
                        timeout=API_TIMEOUT
                    )

                for m in media_group:
                    await db.mark_processed(chat_id, m.id)
                if len(ALBUM_CACHE) > 100:
                    ALBUM_CACHE.clear()
                await db.log_event("SENT", message, "Album mirrored")

            # Обычные сообщения
            else:
                if message.forward_date:
                    await asyncio.wait_for(message.forward(target_id), timeout=API_TIMEOUT)
                else:
                    await asyncio.wait_for(message.copy(target_id), timeout=API_TIMEOUT)

                await db.mark_processed(chat_id, msg_id)
                logger.info(f"✅ Sent Msg {msg_id}")
                await db.log_event("SENT", message, "Message mirrored")

        except asyncio.TimeoutError:
            logger.error(f"⏱️ Worker timeout on Msg {msg_id}, skipping")
            await db.log_event("ERROR", "System", f"Timeout sending Msg {msg_id}")
        except Exception as e:
            logger.error(f"❌ Worker Error: {e}")
            await db.log_event("ERROR", "System", str(e))
        finally:
            msg_queue.task_done()


# --- 3. CATCHUP (догонялка при старте) ---
async def catchup(client, source_id):
    logger.info(f"🔍 Catchup: checking last {HISTORY_DEPTH} messages...")
    messages = []
    async for m in client.get_chat_history(source_id, limit=HISTORY_DEPTH):
        messages.append(m)

    queued = 0
    for message in reversed(messages):  # хронологический порядок
        if not await db.is_processed(message.chat.id, message.id):
            await msg_queue.put(message)
            queued += 1

    logger.info(f"✅ Catchup: queued {queued} unprocessed messages")


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
    global msg_queue, worker_task, _target_id, _source_id
    msg_queue = asyncio.Queue()
    await db.connect()
    logger.info("🚀 Bot Starting (Event Mode)...")
    await app.start()

    try:
        source_id = await resolve_chat(app, SOURCE_CHANNEL)
        target_id = await resolve_chat(app, TARGET_CHANNEL)
        logger.info(f"🎯 Config: {source_id} -> {target_id}")
    except Exception as e:
        logger.error(f"Startup failed: {e}")
        await app.stop()
        return

    _target_id = target_id
    _source_id = source_id

    # Подписываемся на канал-источник и синхронизируем pts сессии
    try:
        await app.join_chat(source_id)
        logger.info(f"✅ Joined source channel {source_id}")
    except Exception as e:
        logger.info(f"ℹ️ join_chat: {e} (likely already a member)")

    # Синхронизируем диалоги — инициализирует pts для всех каналов в сессии,
    # после чего Telegram начинает слать live-апдейты
    logger.info("🔄 Syncing dialogs to initialize channel pts...")
    async for _ in app.get_dialogs():
        pass
    logger.info("✅ Dialogs synced")

    # Обычные сообщения — в очередь
    app.add_handler(MessageHandler(on_new_message, filters.chat(source_id) & ~filters.service))
    # Сервисные события — только в лог
    app.add_handler(MessageHandler(on_service_message, filters.chat(source_id) & filters.service))

    worker_task = asyncio.create_task(worker_loop(app, target_id))
    asyncio.create_task(watchdog_loop())
    asyncio.create_task(keepalive_loop())
    asyncio.create_task(periodic_catchup_loop())

    # Докидываем пропущенные сообщения за время даунтайма
    await catchup(app, source_id)

    # Инициализируем точку отсчёта для fast_poll из БД (после catchup)
    global _last_polled_id
    _last_polled_id = await db.get_max_processed_id(source_id)
    logger.info(f"⚡ Fast poll starting from id={_last_polled_id}")
    asyncio.create_task(fast_poll_loop())

    await idle()
    await app.stop()


if __name__ == "__main__":
    asyncio.run(main())
