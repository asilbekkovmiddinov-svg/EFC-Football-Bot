import asyncio
import logging
import sqlite3
import os
from aiogram import Bot, Dispatcher, F
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiohttp import web
from config import BOT_TOKEN, ADMIN_ID
from database import init_db, DB_NAME
from handlers import wallet, wheel, p2p, match

logging.basicConfig(level=logging.INFO)

def main_menu_keyboard(user_id):
    buttons = [
        [KeyboardButton(text="🧳 Balans va Hamyon"), KeyboardButton(text="🎡 Kunlik G'ildirak")],
        [KeyboardButton(text="💱 P2P Birja"), KeyboardButton(text="⚔️ 1vs1 Match")],
        [KeyboardButton(text="🎫 Oltin Bilet")]
    ]
    if user_id == ADMIN_ID:
        buttons.append([KeyboardButton(text="⚙️ Admin Panel")])
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)
async def handle_index_html(request):
    """Amvera havolasiga kirganda index.html faylini foydalanuvchiga ko'rsatish funksiyasi"""
    try:
        with open("index.html", "r", encoding="utf-8") as f:
            return web.Response(text=f.read(), content_type="text/html")
    except FileNotFoundError:
        return web.Response(text="<h1>404: index.html fayli topilmadi!</h1>", status=404, content_type="text/html")

async def main():
    init_db()
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    
    # Routerlarni ulash
    dp.include_router(wallet.router)
    dp.include_router(wheel.router)
    dp.include_router(p2p.router)
    dp.include_router(match.router)
    
    @dp.message(F.text == "/start")
    async def cmd_start(message):
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)", (message.from_user.id, message.from_user.username))
        conn.commit()
        conn.close()
        
        await message.answer(
            f"👋 Salom, {message.from_user.full_name}!\neFootball EFC ekotizim botiga xush kelibsiz.\nQuyidagi menyudan foydalaning:",
            reply_markup=main_menu_keyboard(message.from_user.id)
        )

    print("🚀 Bot muvaffaqiyatli ishga tushdi va barcha tizimlar ulandi!")
    await bot.delete_webhook(drop_pending_updates=True)
    
    # Veb server va Telegram botni birga ishga tushiramiz
    app = web.Application()
    app.router.add_get("/", handle_index_html)
    
    # Amvera taqdim etadigan PORT orqali ishlaydi (sukut bo'yicha 80 or 8080)
    port = int(os.environ.get("PORT", 80))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    
    # Bir vaqtda ham saytni, ham bot pollingni yoqamiz
    await asyncio.gather(
        site.start(),
        dp.start_polling(bot)
    )

if __name__ == "__main__":
    asyncio.run(main())
    
