# handlers/wheel.py
import sqlite3
import random
import datetime
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from database import DB_NAME

router = Router()

# Oddiy va tasodifiy chiqadigan yutuqlar ro'yxati (Global yutuqlardan tashqari)
STANDARD_PRIZES = ["1efc", "10efc", "50efc", "0 (Yutqazish)"]

def get_user_spins(user_id):
    """Foydalanuvchining reklama orqali qo'shimcha aylantirishlarini boshqarish uchun vaqtinchalik yoki bazaviy tizim"""
    # Bu yerda har bir foydalanuvchining kunlik reklama ko'rish sonini saqlash mumkin
    return 0

@router.message(F.text == "🎡 Kunlik G'ildirak")
async def wheel_menu(message: Message):
    user_id = message.from_user.id
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT last_wheel_time FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    
    can_spin_free = True
    if row and row[0]:
        last_time = datetime.datetime.fromisoformat(row[0])
        now = datetime.datetime.now()
        # 1 soat o'tganini tekshirish
        if now - last_time < datetime.timedelta(hours=1):
            can_spin_free = False
            remaining = datetime.timedelta(hours=1) - (now - last_time)
            minutes = int(remaining.total_seconds() // 60)
            status_text = f"⏳ Bepul aylantirish yopiq. {minutes} daqiqadan keyin ochiladi."
        else:
            status_text = "✅ 1 ta Bepul aylantirish mavjud!"
    else:
        status_text = "✅ 1 ta Bepul aylantirish mavjud!"

    text = (
        f"🎡 **Omad G'ildiragi bo'limi**\n\n"
        f"🎁 Sovrinlar: 1 EFC, 10 EFC, 50 EFC, 250 EFC, 130 Coin, 2000 Coin.\n"
        f"📊 Holat: {status_text}\n\n"
        f"ℹ️ Agar bepul imkoniyat tugagan bo'lsa, AdsGram orqali 2 ta video ko'rib qayta aylantirishingiz mumkin!"
    )
    
    buttons = []
    if can_spin_free:
        buttons.append([InlineKeyboardButton(text="🎰 Bepul aylantirish (1 soatda 1ta)", callback_data="spin_wheel_free")])
    else:
        buttons.append([InlineKeyboardButton(text="📺 Video ko'rib aylantirish (AdsGram)", callback_data="spin_wheel_ads")])
        
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await message.answer(text, reply_markup=kb, parse_mode="Markdown")

@router.callback_query(F.data.startswith("spin_wheel_"))
async def process_wheel_spin(callback: CallbackQuery):
    user_id = callback.from_user.id
    spin_type = callback.data.split("_")[-1] # free yoki ads
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # 1. Vaqtni tekshirish (Agar bepul bo'lsa)
    if spin_type == "free":
        cursor.execute("SELECT last_wheel_time FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        if row and row[0]:
            last_time = datetime.datetime.fromisoformat(row[0])
            if datetime.datetime.now() - last_time < datetime.timedelta(hours=1):
                conn.close()
                return await callback.answer("⏳ Bepul aylantirish vaqti kelmadi!", show_alert=True)
    
    # 2. Global hisoblagichni oshirish (Har bir bosilgan aylanish jami tizim bo'yicha hisoblanadi)
    cursor.execute("UPDATE wheel_stats SET total_spins = total_spins + 1 WHERE id = 1")
    cursor.execute("SELECT total_spins FROM wheel_stats WHERE id = 1")
    total_spins = cursor.fetchone()[0]
    
    # 3. Aniq yutuq algoritmi (Siz bergan shartlar)
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
        # Oddiy holatda kunlik tasodifiy aylanish yutuqlari chiqadi
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
            prize_text = "❌ Afsuski yutqazdingiz (0 coin)"

    # Vaqtni yangilash (Faqat bepul aylantirgan bo'lsa)
    if spin_type == "free":
        now_str = datetime.datetime.now().isoformat()
        cursor.execute("UPDATE users SET last_wheel_time = ? WHERE user_id = ?", (now_str, user_id))
        
    conn.commit()
    conn.close()
    
    await callback.message.delete()
    await callback.message.answer(
        f"🎉 **G'ildirak aylandi!**\n\n"
        f"Tizimdagi umumiy aylanishlar soni: {total_spins:,}\n"
        f"🎁 Sizning yutug'ingiz: **{prize_text}**",
        parse_mode="Markdown"
    )
    await callback.answer()
  
