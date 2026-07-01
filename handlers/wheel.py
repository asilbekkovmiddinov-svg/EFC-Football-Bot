import sqlite3
import random
import logging
from aiogram import Router, F
from aiogram.types import Message
from database import DB_NAME

router = Router()

# G'ildirak yutuqlari ro'yxati (index.html ichidagi 12 ta sektor tartibida)
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

@router.message(F.web_app_data)
async def web_app_callback(message: Message):
    """G'ildirak oynasi yopilganda Telegram yuboradigan ma'lumotni tutish"""
    user_id = message.from_user.id
    data_text = message.web_app_data.data
    
    # Kelgan signalni tekshiramiz
    if "wheel_spin_success" in data_text:
        # Tasodifiy bitta yutuqni tanlaymiz
        yutuq = random.choice(YUTUQLAR)
        
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        if yutuq["tur"] == "efc":
            cursor.execute("UPDATE users SET balans_efc = balans_efc + ? WHERE user_id = ?", (yutuq["miqdor"], user_id))
            javob = f"🎉 Omad keldi! Sizga **{yutuq['matn']}** taqdim etildi va balansingizga qo'shildi!"
        elif yutuq["tur"] == "coin":
            cursor.execute("UPDATE users SET balans_coin = balans_coin + ? WHERE user_id = ?", (yutuq["miqdor"], user_id))
            javob = f"🎉 Omad keldi! Sizga **{yutuq['matn']}** taqdim etildi va balansingizga qo'shildi!"
        else:
            javob = "😔 Afsuski, g'ildirakda **YUTQAZISH** chiqdi. Keyingi safar albatta omad kulib boqadi!"
            
        conn.commit()
        conn.close()
        
        await message.answer(javob, parse_mode="Markdown")
        
