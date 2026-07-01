import asyncio
import logging
import sqlite3
import os
import random
from aiogram import Bot, Dispatcher, F
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, WebAppInfo
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from config import BOT_TOKEN, ADMIN_ID
from database import init_db, DB_NAME
from handlers import wallet, wheel, p2p, match

logging.basicConfig(level=logging.INFO)
app = FastAPI()
bot_instance = Bot(token=BOT_TOKEN)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

YUTUQLAR = [
    {"tur": "efc", "miqdor": 1, "matn": "1 EFC"},
    {"tur": "yutqazish", "miqdor": 0, "matn": "YUTQAZISH ❌"},
    {"tur": "efc", "miqdor": 10, "matn": "10 EFC"},
    {"tur": "yutqazish", "miqdor": 0, "matn": "YUTQAZISH ❌"},
    {"tur": "efc", "miqdor": 50, "matn": "50 EFC"},
    {"tur": "yutqazish", "miqdor": 0, "matn": "YUTQAZISH ❌"},
    {"tur": "efc", "miqdor": 250, "matn": "250 EFC"},
    {"tur": "yutqazish", "miqdor": 0, "matn": "YUTQAZISH ❌"},
    {"tur": "coin", "miqdor": 130, "matn": "130 COIN"},
    {"tur": "yutqazish", "miqdor": 0, "matn": "YUTQAZISH ❌"},
    {"tur": "coin", "miqdor": 2000, "matn": "2000 COIN"},
    {"tur": "yutqazish", "miqdor": 0, "matn": "YUTQAZISH ❌"}
]

@app.get("/", response_class=HTMLResponse)
async def handle_index_html():
    try:
        with open("index.html", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "<h1>404: index.html topilmadi!</h1>"

@app.get("/spin-reward")
async def spin_reward(user_id: int):
    """Saytdan kelgan to'g'ridan-to'g'ri API so'rovi"""
    if not user_id:
        return {"status": "error", "message": "ID xato"}
        
    yutuq = random.choice(YUTUQLAR)
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    if yutuq["tur"] == "efc":
        cursor.execute("UPDATE users SET balans_efc = balans_efc + ? WHERE user_id = ?", (yutuq["miqdor"], user_id))
        msg = f"🎉 Omad keldi! Sizga **{yutuq['matn']}** taqdim etildi va balansingizga qo'shildi!"
    elif yutuq["tur"] == "coin":
        cursor.execute("UPDATE users SET balans_coin = balans_coin + ? WHERE user_id = ?", (yutuq["miqdor"], user_id))
        msg = f"🎉 Omad keldi! Sizga **{yutuq['matn']}** taqdim etildi va balansingizga qo'shildi!"
    else:
        msg = "😔 Afsuski, g'ildirakda **YUTQAZISH** chiqdi. Keyingi safar albatta omad kulib boqadi!"
        
    conn.commit()
    conn.close()
    
    # Bot orqali foydalanuvchiga darhol Telegramda xabar yuboramiz
    try:
        await bot_instance.send_message(chat_id=user_id, text=msg, parse_mode="Markdown")
    except Exception as e:
        logging.error(f"Xabar yuborishda xato: {e}")
        
    return {"status": "success", "message": "Natija saqlandi!"}

def main_menu_keyboard(user_id):
    buttons = [
        [KeyboardButton(text="🎡 Omad g'ildiragi", web_app=WebAppInfo(url="https://efcfootball.uz"))],
        [KeyboardButton(text="🧳 Balans va Hamyon"), KeyboardButton(text="💱 P2P Birja")],
        [KeyboardButton(text="⚔️ 1vs1 Match"), KeyboardButton(text="🎫 Oltin Bilet")],
        [KeyboardButton(text="👥 Takliflar (Referal)")]
    ]
    if user_id == ADMIN_ID:
        buttons.append([KeyboardButton(text="⚙️ Admin Panel")])
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

async def start_telegram_bot():
    init_db()
    dp = Dispatcher()
    
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
        referrer_id = int(args) if len(args) > 1 and args.isdigit() else 0
        
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
        user_exists = cursor.fetchone()
        
        if not user_exists:
            if referrer_id and referrer_id != user_id:
                cursor.execute("INSERT INTO users (user_id, username, referred_by) VALUES (?, ?, ?)", (user_id, username, referrer_id))
                cursor.execute("UPDATE users SET balans_efc = balans_efc + 50 WHERE user_id = ?", (referrer_id,))
                try:
                    await bot_instance.send_message(chat_id=referrer_id, text=f"👥 **Yangi referal!**\n\nSizning havolangiz orqali {full_name} botga kirdi. +50 EFC bonus qo'shildi!")
                except: pass
            else:
                cursor.execute("INSERT INTO users (user_id, username) VALUES (?, ?)", (user_id, username))
            conn.commit()
        conn.close()
        
        await message.answer(
            f"👋 Salom, {full_name}!\neFootball EFC ekotizim botiga xush kelibsiz.\n\n"
            f"🎡 Omad g'ildiragini aylantirish uchun pastdagi yangi **'🎡 Omad g'ildiragi'** tugmasini bosing!",
            reply_markup=main_menu_keyboard(user_id)
        )

    @dp.message(F.text == "👥 Takliflar (Referal)")
    async def referral_menu(message):
        user_id = message.from_user.id
        bot_info = await bot_instance.get_me()
        ref_link = f"https://t.me{bot_info.username}?start={user_id}"
        
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users WHERE referred_by = ?", (user_id,))
        total_referrals = cursor.fetchone()
        conn.close()
        
        text = (
            f"👥 **Referal tizimi**\n\n"
            f"Botga do'stlaringizni taklif qiling va har bir faol do'stingiz uchun **50 EFC** bonusga ega bo'ling!\n\n"
            f"📊 Siz taklif qilgan do'stlar: **{total_referrals} ta**\n\n"
            f"🔗 Sizning taklif havolangiz:\n`{ref_link}`\n\n"
            f"*(Havolani ustiga bossangiz, avtomatik nusxalanadi. Uni do'stolaringizga tarqating!)*"
        )
        await message.answer(text, parse_mode="Markdown")

    await bot_instance.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot_instance)

@app.on_event("startup")
async def on_startup():
    asyncio.create_task(start_telegram_bot())

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 80))
    uvicorn.run(app, host="0.0.0.0", port=port)
    
