import asyncio
import logging
import sqlite3
import os
from aiogram import Bot, Dispatcher, F
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from config import BOT_TOKEN, ADMIN_ID
from database import init_db, DB_NAME
from handlers import wallet, wheel, p2p, match

logging.basicConfig(level=logging.INFO)

# FastAPI veb-serverini yaratamiz
app = FastAPI()

# Brauzerlarda JavaScript bloklanib qolmasligi uchun CORS xavfsizligini yoqamiz
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", response_class=HTMLResponse)
async def handle_index_html():
    """Veb-sayt manzili chaqirilganda bosh papkadagi index.html faylini o'qib ko'rsatish"""
    try:
        with open("index.html", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "<h1>404: index.html fayli bosh papkada topilmadi!</h1>"

def main_menu_keyboard(user_id):
    buttons = [
        [KeyboardButton(text="🧳 Balans va Hamyon"), KeyboardButton(text="💱 P2P Birja")],
        [KeyboardButton(text="⚔️ 1vs1 Match"), KeyboardButton(text="🎫 Oltin Bilet")],
        [KeyboardButton(text="👥 Takliflar (Referal)")]
    ]
    if user_id == ADMIN_ID:
        buttons.append([KeyboardButton(text="⚙️ Admin Panel")])
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

async def start_telegram_bot():
    """Botni alohida fonda ishga tushirish funksiyasi"""
    init_db()
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    
    # Routerlarni ulash
    dp.include_router(wheel.router)
    dp.include_router(p2p.router)
    dp.include_router(match.router)
    dp.include_router(wallet.router)
    
    @dp.message(F.text == "/start")
    async def cmd_start(message):
        user_id = message.from_user.id
        username = message.from_user.username
        full_name = message.from_user.full_name
        
        args = message.text.split()
        referrer_id = int(args[1]) if len(args) > 1 and args[1].isdigit() else 0
        
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
        user_exists = cursor.fetchone()
        
        if not user_exists:
            if referrer_id and referrer_id != user_id:
                cursor.execute("INSERT INTO users (user_id, username, referred_by) VALUES (?, ?, ?)", (user_id, username, referrer_id))
                cursor.execute("UPDATE users SET balans_efc = balans_efc + 50 WHERE user_id = ?", (referrer_id,))
                try:
                    await bot.send_message(
                        chat_id=referrer_id, 
                        text=f"👥 **Yangi referal!**\n\nSizning havolangiz orqali {full_name} botga kirdi. Balansingizga +50 EFC bonus qo'shildi!"
                    )
                except: pass
            else:
                cursor.execute("INSERT INTO users (user_id, username) VALUES (?, ?)", (user_id, username))
            conn.commit()
        conn.close()
        
        await message.answer(
            f"👋 Salom, {full_name}!\neFootball EFC ekotizim botiga xush kelibsiz.\n\n"
            f"🎡 Omad g'ildiragini aylantirish uchun chap pastdagi ko'k tugmani bosing!",
            reply_markup=main_menu_keyboard(user_id)
        )

    @dp.message(F.text == "👥 Takliflar (Referal)")
    async def referral_menu(message):
        user_id = message.from_user.id
        bot_info = await bot.get_me()
        ref_link = f"https://t.me{bot_info.username}?start={user_id}"
        
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users WHERE referred_by = ?", (user_id,))
        total_referrals = cursor.fetchone()[0]
        conn.close()
        
        text = (
            f"👥 **Referal tizimi**\n\n"
            f"Botga do'stlaringizni taklif qiling va har bir faol do'stingiz uchun **50 EFC** bonusga ega bo'ling!\n\n"
            f"📊 Siz taklif qilgan do'stlar: **{total_referrals} ta**\n\n"
            f"🔗 Sizning taklif havolangiz:\n`{ref_link}`\n\n"
            f"*(Havolani ustiga bossangiz, avtomatik nusxalanadi. Uni do'stlaringizga tarqating!)*"
        )
        await message.answer(text, parse_mode="Markdown")

    logging.info("🚀 Telegram bot orqa fonda muvaffaqiyatli yuklandi!")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

@app.on_event("startup")
async def on_startup():
    """FastAPI serveri yonishi bilan botni parallel ravishda ishga tushiramiz"""
    asyncio.create_task(start_telegram_bot())

if __name__ == "__main__":
    # Amvera porti orqali FastAPI serverini asosiy zanjirda yoqamiz
    port = int(os.environ.get("PORT", 80))
    uvicorn.run(app, host="0.0.0.0", port=port)
    
