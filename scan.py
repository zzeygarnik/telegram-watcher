from pyrogram import Client
from config import API_ID, API_HASH

# Создаем простого клиента без базы данных и сложной логики
app = Client("scanner_session", api_id=API_ID, api_hash=API_HASH)

print("🕵️ СКАНЕР ЗАПУЩЕН. Напиши что-нибудь в канал-источник...", flush=True)

# Этот хендлер ловит ВООБЩЕ ВСЕ (без фильтров по ID)
@app.on_message()
async def monitor(client, message):
    chat = message.chat
    print(f"\n📨 ПОЙМАЛ СООБЩЕНИЕ!", flush=True)
    print(f"   От канала: '{chat.title}'", flush=True)
    print(f"   Юзернейм: @{chat.username}", flush=True)
    print(f"   📛 REAL ID: {chat.id}  <--- КОПИРУЙ ЭТОТ НОМЕР", flush=True)
    print(f"   Текст: {message.text[:20] if message.text else 'Медиа...'}", flush=True)

app.run()