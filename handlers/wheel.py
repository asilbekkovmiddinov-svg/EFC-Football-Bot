import sqlite3
import random
import datetime
import json
from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.fsm.context import FSMContext
from database import DB_NAME

router = Router()
STANDARD_PRIZES = ["1efc", "10efc", "50efc", "yutqazish", "yutqazish", "yutqazish"]

@router.message(F.text == "🎡 Kunlik G'ildirak")
async def wheel_menu(message: Message, state: FSMContext):
    await state.clear()  # Pul kiritishda adashib qolgan bo'lsa, holatni avtomat tozalaydi!
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
    
    # Yangi kun kelganda video ko'rish sonini 0 ga tushiramiz
    if last_video_date != today_str:
        video_count = 0
        cursor.execute("UPDATE users SET video_spins_count = 0, last_video_spin_date = ? WHERE user_id = ?", (today_str, user_id))
        conn.commit()

    # 1. Bepul aylantirishni tekshirish (1 kunda 1 marta)
    can_spin_free = True
    free_status = "✅ Mavjud"
    if last_free_time:
        last_time = datetime.datetime.fromisoformat(last_free_time)
        if now.date() == last_time.date():
            can_spin_free = False
            free_status = "❌ Bugun foydalanilgan (Ertaga ochiladi)"

    # 2. Video orqali aylantirishni tekshirish (Kuniga 5 ta, har 1 soatda 1 ta)
    can_spin_video = False
    video_status = ""
    
    if not can_spin_free:  # Agar bepul urinish tugagan bo'lsa, videoni tekshiramiz
        if video_count < 5:
            if last_video_date == today_str and last_free_time:
                # Oxirgi aylanishdan (bepul yoki video) 1 soat o'tganini tekshiramiz
                last_any_spin = datetime.datetime.fromisoformat(last_free_time)
                if now - last_any_spin >= datetime.timedelta(hours=1):
                    can_spin_video = True
                    video_status = f"✅ Video ko'rish mavjud ({video_count}/5)"
                else:
                    remaining = datetime.timedelta(hours=1) - (now - last_any_spin)
                    minutes = int(remaining.total_seconds() // 60)
                    video_status = f"⏳ Video {minutes} daqiqadan keyin ochiladi ({video_count}/5)"
            else:
                can_spin_video = True
                video_status = f"✅ Video ko'rish mavjud ({video_count}/5)"
        else:
            video_status = "❌ Bugungi barcha 5 ta video ko'rib bo'lindi"

    text = (
        f"🎡 **Omad G'ildiragi bo'limi**\n\n"
        f"🎁 Bepul aylantirish (1 kunda 1ta): {free_status}\n"
        f"📺 Reklama orqali (Kuniga 5ta / 1 soatda 1ta): {video_status}\n\n"
        f"ℹ️ Tizimda 15k, 30k va 60k global aylanishlarga super yutuqlar saqlangan!"
    )
    
    buttons = []
    if can_spin_free:
        buttons.append([InlineKeyboardButton(text="🎰 1 kunlik Bepul aylantirish", web_app=WebAppInfo(url=MINI_APP_URL))])
    elif can_spin_video:
        buttons.append([InlineKeyboardButton(text="📺 Video ko'rib aylantirish (AdsGram)", web_app=WebAppInfo(url=MINI_APP_URL))])
        
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
        
        if last_video_date != today_str:
            video_count = 0

        # Aylanish turini aniqlash
        is_free_spin = True
        if last_free_time:
            last_time = datetime.datetime.fromisoformat(last_free_time)
            # Agar oxirgi aylanish aynan bugun bo'lgan bo'lsa, demak bu bepul emas, video urinish
            if now.date() == last_time.date():
                is_free_spin = False

        # Cheklovlarni bazada yangilash va 1 soatlik taymerni yangilash
        now_str = now.isoformat()
        if is_free_spin:
            cursor.execute("UPDATE users SET last_wheel_time = ? WHERE user_id = ?", (now_str, user_id))
        else:
            if video_count >= 5:
                conn.close()
                return await message.answer("❌ Bugun barcha 5 ta video ko'rish imkoniyatingizdan foydalanib bo'ldingiz!")
            video_count += 1
            # Videodan keyin ham 1 soat kuttirish uchun last_wheel_time ga hozirgi vaqtni yozamiz
            cursor.execute("UPDATE users SET video_spins_count = ?, last_video_spin_date = ?, last_wheel_time = ? WHERE user_id = ?", 
                           (video_count, today_str, now_str, user_id))
        
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
            f"ℹ️ Aylanish turi: {spin_type_msg}\n"
            f"📊 Tizimdagi umumiy aylanishlar: {total_spins:,}\n"
            f"🎁 Sizning yutug'ingiz: **{prize_text}**",
            parse_mode="Markdown"
        )
        
