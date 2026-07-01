import asyncio
import logging
import sqlite3
import os
import json
from aiogram import Bot, Dispatcher, F
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, PlainTextResponse
import uvicorn
from config import BOT_TOKEN, ADMIN_ID
from database import init_db, DB_NAME
from handlers import wallet, wheel, p2p, match

logging.basicConfig(level=logging.INFO)

# FastAPI veb-serverini yaratamiz
app = FastAPI()
bot_instance = Bot(token=BOT_TOKEN)

@app.get("/", response_class=HTMLResponse)
async def handle_index_html():
    """Amvera havolasiga kirganda index.html faylini ko'rsatish"""
    try:
        with open("index.html", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "<h1>404: index.html fayli bosh papkada topilmadi!</h1>"

@app.get("/adsgram-callback", response_class=PlainTextResponse)
async def adsgram_webhook(request: Request):
    """AdsGram videosi oxirigacha ko'rilganda keladigan rasmiy callback datchigi"""
    params = dict(request.query_params)
    user_id = params.get("user")
    status = params.get("status") # 'reward' yoki 'render' keladi

    # AdsGram muvaffaqiyatli ko'rildi deb signal yuborgan bo'lsa
    if user_id and status == "reward":
        try:
            uid = int(user_id)
            # Foydalanuvchiga botdan to'g'ridan-to'g'ri bildirishnoma yuborish mumkin
            # (Asosiy mukofot baribir Mini App yopilganda wheel.py orqali hisoblanadi)
            logging.info(f"🟢 AdsGram muvaffaqiyatli callback keldi! User: {uid}")
        except ValueError:
            pass
            
    return "OK"

def main_menu_keyboard(user_id):
    buttons = [
        [KeyboardButton(text="🧳 Balans va Hamyon"), KeyboardButton(text="💱 P2P Birja")],
        [KeyboardButton(text="⚔️ 1vs1 Match"), KeyboardButton(text="🎫 Oltin Bilet")],
        [KeyboardButton(text="👥 Takliflar (Referal)")]
    ]
    if user_id == ADMIN_ID:
        buttons.append([KeyboardButton(text="⚙️ Admin Panel")])
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

async def run_bot():
    init_db()
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
                    await bot_instance.send_message(
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
            f"📊 Siz taklif qilgan do'stlar: **{total_referrals[0]} ta**\n\n"
            f"🔗 Sizning taklif havolangiz:\n`{ref_link}`\n\n"
            f"*(Havolani ustiga bossangiz, avtomatik nusxalanadi. Uni do'stlaringizga tarqating!)*"
        )
        await message.answer(text, parse_mode="Markdown")

    print("🚀 Bot muvaffaqiyatli ishga tushdi!")
    await bot_instance.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot_instance)

async def main():
    port = int(os.environ.get("PORT", 80))
    config = uvicorn.Config(app, host="0.0.0.0", port=port, log_level="info")
    server = uvicorn.Server(config)
    
    await asyncio.gather(
        server.serve(),
        run_bot()
    )

if __name__ == "__main__":
    asyncio.run(main())
    
