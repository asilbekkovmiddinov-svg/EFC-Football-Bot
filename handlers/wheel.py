import sqlite3
import random
import datetime
import json
from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from database import DB_NAME

router = Router()
STANDARD_PRIZES = ["1efc", "10efc", "50efc", "0 (Yutqazish)"]

@router.message(F.text == "🎡 Kunlik G'ildirak")
async def wheel_menu(message: Message):
    # TAYYOR AMVERA HAVOLASI SHU YERGA YOZILDI
    MINI_APP_URL = "https://asilbekkovmiddinov-svg.github.io/EFC-Football-Bot/"
    
    text = (
        f"🎡 **Omad G'ildiragi (Mini App)**\n\n"
        f"G'ildirakni aylantirish uchun pastdagi tugmani bosing va ochilgan oynada AdsGram videosini tomosha qiling!\n\n"
        f"🎁 Esda tuting: 15k, 30k va 60k global aylanishlarga super yutuqlar bor!"
    )
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎰 G'ildirakni ochish 📺", web_app=WebAppInfo(url=MINI_APP_URL))]
    ])
    await message.answer(text, reply_markup=kb, parse_mode="Markdown")
@router.message(F.web_app_data)
async def handle_mini_app_data(message: Message):
    data = json.loads(message.web_app_data.data)
    if data.get("action") == "wheel_spin_success":
        user_id = message.from_user.id
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("UPDATE wheel_stats SET total_spins = total_spins + 1 WHERE id = 1")
        cursor.execute("SELECT total_spins FROM wheel_stats WHERE id = 1")
        total_spins = cursor.fetchone()[0]
        prize_text = ""
        if total_spins == 60000:
            prize_text = "🎁 KATTA YUTUQ! 2000 Coin"
            cursor.execute("UPDATE users SET balans_coin = balans_coin + 2000 WHERE user_id = ?", (user_id,))
        elif total_spins == 30000:
            prize_text = "🎁 YUTUQ! 130 Coin"
            cursor.execute("UPDATE users SET balans_coin = balans_coin + 130 WHERE user_id = ?", (user_id,))
        elif total_spins == 15000:
            prize_text = "🎁 YUTUQ! 250 EFC"
            cursor.execute("UPDATE users SET balans_efc = balans_efc + 250 WHERE user_id = ?", (user_id,))
        else:
            chosen = random.choice(STANDARD_PRIZES)
            if chosen == "1efc":
                prize_text = "1 EFC"
                cursor.execute("UPDATE users SET balans_efc = balans_efc + 1 WHERE user_id = ?", (user_id,))
            elif chosen == "10efc":
                prize_text = "10 EFC"
                cursor.execute("UPDATE users SET balans_efc = balans_efc + 10 WHERE user_id = ?", (user_id,))
            elif chosen == "50efc":
                prize_text = "50 EFC"
                cursor.execute("UPDATE users SET balans_efc = balans_efc + 50 WHERE user_id = ?", (user_id,))
            else:
                prize_text = "❌ Afsuski bu safar yutqazdingiz (0 coin)"
        conn.commit()
        conn.close()
        await message.answer(
            f"🎉 **Video muvaffaqiyatli ko'rildi va G'ildirak aylandi!**\n\n"
            f"📊 Umumiy aylanishlar soni: {total_spins:,}\n"
            f"🎁 Sizning yutug'ingiz: **{prize_text}**",
            parse_mode="Markdown"
        )
    
