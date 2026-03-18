import asyncio
from pyrogram import Client
from config import API_ID, API_HASH

async def auth():
    app = Client("my_mirror_bot", api_id=API_ID, api_hash=API_HASH)
    await app.start()
    print("Session OK! File: my_mirror_bot.session")
    await app.stop()

asyncio.run(auth())
