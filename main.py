# main.py
import asyncio
import logging
from aiogram import Bot, Dispatcher
from config import BOT_TOKEN
from database import init_db

# Handlers (Keyingi qadamda yozamiz, hozircha import qilmaymiz)
# To'liq kod ishlashi uchun bular keyin ulanadi.

logging.basicConfig(level=logging.INFO)

async def main():
    # Bazani tekshirish va yaratish
    init_db()
    
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    
    # Routers (Yo'naltirgichlarni ulash)
    # Unders/Handlers yozilgach bu yerga qo'shiladi
    
    print("Bot muvaffaqiyatli ishga tushdi...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
  
