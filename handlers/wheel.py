import sqlite3
import random
import datetime
import json
from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from database import DB_NAME

router = Router()
# 3 ta yutqazish va 3 ta yutuq varianti (50% ga 50% ehtimollik uchun)
STANDARD_PRIZES = ["1efc", "10efc", "50efc", "yutqazish", "yutqazish", "yutqazish"]

@router.message(F.text == "🎡 Kunlik G'ildirak")
async def wheel_menu(message: Message):
    user_id = message.from_user.id
    MINI_APP_URL = "https://asilbekkovmiddinov-svg.github.io/EFC-Football-Bot/"
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT last_wheel_time, video_spins_count, last_video_spin_date FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    
    if not row:
        cursor.execute("INSERT INTO users (user_id, username) VALUES (?, ?)", (user_id, message.from_user.username))
        conn.commit()
        row = (None, 0, None)
        
    last_free_time, video_count, last_video_date = row
    now = datetime.datetime.now()
    today_str = now.date().isoformat()
    
    # Kun yangilanganda video hisoblagichni 0 ga qaytarish
    if last_video_date != today_str:
        video_count = 0
        cursor.execute("UPDATE users SET video_spins_count = 0, last_video_spin_date = ? WHERE user_id = ?", (today_str, user_id))
        conn.commit()

    # Bepul aylantirish taymerini tekshirish (1 soat)
    can_spin_free = True
    status_text = "✅ 1 ta Bepul aylantirish mavjud!"
    if last_free_time:
        last_time = datetime.datetime.fromisoformat(last_free_time)
        if now - last_time < datetime.timedelta(hours=1):
            can_spin_free = False
            remaining = datetime.timedelta(hours=1) - (now - last_time)
            minutes = int(remaining.total_seconds() // 60)
            status_text = f"⏳ Bepul aylantirish yopiq. {minutes} daqiqadan keyin ochiladi."

    text = (
        f"🎡 **Omad G'ildiragi bo'limi**\n\n"
        f"📊 Bepul aylantirish: {status_text}\n"
        f"📺 Reklama orqali aylanish: Bugun {video_count}/5 ta video ko'rdingiz.\n\n"
        f"ℹ️ Har 1 soatda 1 marta bepul va kuniga 5 marta video ko'rib aylantirish imkoniyatingiz bor!"
    )
    
    buttons = []
    if can_spin_free:
        buttons.append([InlineKeyboardButton(text="🎰 Bepul aylantirish (Mini App)", web_app=WebAppInfo(url=MINI_APP_URL))])
    elif video_count < 5:
        buttons.append([InlineKeyboardButton(text="📺 Video ko'rib aylantirish (Mini App)", web_app=WebAppInfo(url=MINI_APP_URL))])
    else:
        text += "\n\n❌ Bugungi barcha bepul va video imkoniyatlaringiz tugadi. Ertaga qayta urinib ko'ring!"
        
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    conn.close()
    await message.answer(text, reply_markup=kb, parse_mode="Markdown")
@router.message(F.web_app_data)
async def handle_mini_app_data(message: Message):
    data = json.loads(message.web_app_data.data)
    if data.get("action") == "wheel_spin_success":
        user_id = message.from_user.id
        now = datetime.datetime.now()
        today_str = now.date().isoformat()
        
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # Foydalanuvchining joriy holatini tekshirish
        cursor.execute("SELECT last_wheel_time, video_spins_count, last_video_spin_date FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        last_free_time, video_count, last_video_date = row if row else (None, 0, None)
        
        # Kun yangilangan bo'lsa video hisoblagichni yangilash
        if last_video_date != today_str:
            video_count = 0

        # Aylanish turini aniqlash (Bepul yoki Video)
        is_free_spin = True
        if last_free_time:
            last_time = datetime.datetime.fromisoformat(last_free_time)
            if now - last_time < datetime.timedelta(hours=1):
                is_free_spin = False # Bepul vaqti kelmagan, demak video orqali aylantirdi

        # Cheklovlarni bazada yangilash
        if is_free_spin:
            now_str = now.isoformat()
            cursor.execute("UPDATE users SET last_wheel_time = ? WHERE user_id = ?", (now_str, user_id))
        else:
            if video_count >= 5:
                conn.close()
                return await message.answer("❌ Bugun barcha 5 ta video ko'rish imkoniyatingizdan foydalanib bo'ldingiz!")
            video_count += 1
            cursor.execute("UPDATE users SET video_spins_count = ?, last_video_spin_date = ? WHERE user_id = ?", (video_count, today_str, user_id))
        
        # ----------------- GLOBAL VA RANDOM YUTUQ ALGORITMI -----------------
        cursor.execute("UPDATE wheel_stats SET total_spins = total_spins + 1 WHERE id = 1")
        cursor.execute("SELECT total_spins FROM wheel_stats WHERE id = 1")
        total_spins = cursor.fetchone()[0]
        
        prize_text = ""
        if total_spins == 60000:
            prize_text = "🎁 KATTA SUPER YUTUQ! 2000 Coin"
            cursor.execute("UPDATE users SET balans_coin = balans_coin + 2000 WHERE user_id = ?", (user_id,))
        elif total_spins == 30000:
            prize_text = "🎁 OMADLI YUTUQ! 130 Coin"
            cursor.execute("UPDATE users SET balans_coin = balans_coin + 130 WHERE user_id = ?", (user_id,))
        elif total_spins == 15000:
            prize_text = "🎁 YUTUQ! 250 EFC"
            cursor.execute("UPDATE users SET balans_efc = balans_efc + 250 WHERE user_id = ?", (user_id,))
        else:
            # 50% ga 50% tasodifiy ehtimollik algoritmi
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
                prize_text = "❌ Afsuski, bu safar yutqazdingiz (0 mukofot)"
                
        conn.commit()
        conn.close()
        
        # Foydalanuvchiga yakuniy xabar
        spin_type_msg = "Bepul urinish" if is_free_spin else f"📺 Video reklama ({video_count}/5)"
        await message.answer(
            f"🎉 **G'ildirak muvaffaqiyatli aylandi!**\n\n"
            f"ℹ️ Aylanish turi: {spin_type_msg}\n"
            f"📊 Tizimdagi umumiy aylanishlar: {total_spins:,}\n"
            f"🎁 Sizning yutug'ingiz: **{prize_text}**",
            parse_mode="Markdown"
        )
        
