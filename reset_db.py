import asyncio
import sys
import os

# ИСПРАВЛЕНО: Добавлены двойные подчеркивания вокруг file
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

# Пытаемся импортировать конфиг
try:
    import config
except ImportError:
    # Если не вышло, пробуем добавить текущую рабочую директорию
    sys.path.append(os.getcwd())
    import config

import asyncpg

# ID сообщений для удаления
TARGET_IDS = [15786, 15785, 15784, 15783, 15782]

async def reset_messages():
    print(f"🧹 Подключаюсь к БД {config.DB_HOST}...")
    
    try:
        # Подключение напрямую
        conn = await asyncpg.connect(
            user=config.DB_USER,
            password=config.DB_PASS,
            database=config.DB_NAME,
            host=config.DB_HOST,
            port=config.DB_PORT
        )
        print("✅ Подключение успешно!")
    except Exception as e:
        print(f"❌ ОШИБКА ПОДКЛЮЧЕНИЯ: {e}")
        return

    print(f"🔍 Удаляю информацию о сообщениях: {TARGET_IDS}")
    
    try:
        # Выполняем SQL DELETE
        result = await conn.execute(
            "DELETE FROM posted_messages WHERE msg_id = ANY($1::int[])", 
            TARGET_IDS
        )
        print(f"✅ УСПЕХ! Результат операции: {result}")
    except Exception as e:
        print(f"❌ Ошибка SQL: {e}")
    finally:
        await conn.close()

# ИСПРАВЛЕНО: Добавлены двойные подчеркивания вокруг name и main
if __name__ == "__main__":
    asyncio.run(reset_messages())