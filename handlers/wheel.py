import sqlite3
import random
import datetime
import json
from aiogram import Router, F
from aiogram.types import Message
from database import DB_NAME

router = Router()
STANDARD_PRIZES = ["1efc", "10efc", "50efc", "yutqazish", "yutqazish", "yutqazish"]

@router.message(F.web_app_data)
async def handle_mini_app_data(message: Message):
    data = json.loads(message.web_app_data.data)
    if data.get("action") == "wheel_spin_success":
        user_id = message.from_user.id
        now = datetime.datetime.now()
        today_str = now.date().isoformat()
        
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT last_wheel_time, video_spins_count, last_video_spin_date FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        
        if not row:
            cursor.execute("INSERT INTO users (user_id, username) VALUES (?, ?)", (user_id, message.from_user.username))
            conn.commit()
            row = (None, 0, None)
            
        last_free_time, video_count, last_video_date = row
        
        if last_video_date != today_str:
            video_count = 0

        # Algoritm: Bugun umuman aylantirmagan bo'lsa - bu TEKIN (Bepul) urinish bo'ladi
        is_free_spin = True
        if last_free_time:
            last_time = datetime.datetime.fromisoformat(last_free_time)
            if now.date() == last_time.date():
                is_free_spin = False # Bugun allachon aylantirgan, demak bu video urinish

        now_str = now.isoformat()
        if is_free_spin:
            # Bepul urinish sifatida saqlaymiz
            cursor.execute("UPDATE users SET last_wheel_time = ? WHERE user_id = ?", (now_str, user_id))
        else:
            # Video urinish bo'lsa - cheklovlarni tekshiramiz (Kuniga 5 marta, har 1 soatda 1 marta)
            if video_count >= 5:
                conn.close()
                return await message.answer("❌ Bugun barcha 5 ta video ko'rish imkoniyatingizdan foydalanib bo'ldingiz! Ertaga qayta urinib ko'ring.")
            
            # 1 soatlik taymerni tekshirish
            last_time = datetime.datetime.fromisoformat(last_free_time)
            if now - last_time < datetime.timedelta(hours=1):
                remaining = datetime.timedelta(hours=1) - (now - last_time)
                minutes = int(remaining.total_seconds() // 60)
                conn.close()
                return await message.answer(f"⏳ Video orqali aylantirish hali yopiq. Iltimos, {minutes} daqiqa kuting!")

            video_count += 1
            cursor.execute("UPDATE users SET video_spins_count = ?, last_video_spin_date = ?, last_wheel_time = ? WHERE user_id = ?", 
                           (video_count, today_str, now_str, user_id))
        
        # ----------------- REJA BO'YICHA YUTUQLAR -----------------
        cursor.execute("UPDATE wheel_stats SET total_spins = total_spins + 1 WHERE id = 1")
        cursor.execute("SELECT total_spins FROM wheel_stats WHERE id = 1")
        total_spins = cursor.fetchone()
        
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
        
        spin_type_msg = "1 kunlik Bepul urinish" if is_free_spin else f"📺 Video reklama ({video_count}/5)"
        await message.answer(
            f"🎉 **G'ildirak muvaffaqiyatli aylandi!**\n\n"
            f"ℹ️ Urinish turi: {spin_type_msg}\n"
            f"📊 Tizimdagi jami aylanishlar: {total_spins:,}\n"
            f"🎁 Sizning yutug'ingiz: **{prize_text}**",
            parse_mode="Markdown"
        )
        
