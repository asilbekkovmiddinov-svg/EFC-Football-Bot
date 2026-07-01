import sqlite3
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from config import ADMIN_ID, KANAL_ID, MATCH_COMMISSION, BILET_P2P_COMMISSION
from database import DB_NAME

router = Router()

class MatchState(StatesGroup):
    WAITING_FOR_BET = State()
    WAITING_FOR_SCREENSHOT = State()

class TicketState(StatesGroup):
    WAITING_FOR_PRICE = State()

class AdminState(StatesGroup):
    WAITING_FOR_BROADCAST = State()

@router.message(F.text == "⚔️ 1vs1 Match")
async def match_menu(message: Message):
    text = (
        f"⚔️ **eFootball 1vs1 Match xonalari**\n\n"
        f"Raqib bilan EFC tikib o'yin o'ynash bo'limi.\n"
        f"⚠️ **Qoida:** G'olibdan **{MATCH_COMMISSION*100}%** komissiya olinadi.\n"
        f"O'yin tugagach, screenshot yuklash shart."
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Xona yaratish", callback_data="match_create")],
        [InlineKeyboardButton(text="🎮 Ochiq xonalar", callback_data="match_list")]
    ])
    await message.answer(text, reply_markup=kb, parse_mode="Markdown")

@router.callback_query(F.data == "match_create")
async def start_match(callback: CallbackQuery, state: FSMContext):
    await callback.message.delete()
    await callback.message.answer("Xonaga qancha EFC tikmoqchisiz? Miqdorini kiriting:")
    await state.set_state(MatchState.WAITING_FOR_BET)

@router.message(MatchState.WAITING_FOR_BET)
async def process_match_bet(message: Message, state: FSMContext):
    try:
        bet = float(message.text)
        if bet <= 0: raise ValueError
    except ValueError:
        return await message.answer("Iltimos, to'g'ri miqdor kiriting:")
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT balans_efc FROM users WHERE user_id = ?", (message.from_user.id,))
    user_efc = cursor.fetchone()[0] or 0
    if user_efc < bet:
        conn.close()
        await state.clear()
        return await message.answer(f"❌ Balansda yetarli EFC yo'q! Sizda: {user_efc:,} EFC")
    cursor.execute("UPDATE users SET balans_efc = balans_efc - ? WHERE user_id = ?", (bet, message.from_user.id))
    cursor.execute("INSERT INTO match_rooms (creator_id, bet_efc) VALUES (?, ?)", (message.from_user.id, bet))
    conn.commit()
    conn.close()
    await state.clear()
    await message.answer(f"✅ Xona yaratildi! {bet:,} EFC o'yinga tikildi. Raqib kutilmoqda...")

@router.callback_query(F.data == "match_list")
async def show_matches(callback: CallbackQuery):
    await callback.message.delete()
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT room_id, creator_id, bet_efc FROM match_rooms WHERE status = 'kutilmoqda' AND creator_id != ?", (callback.from_user.id,))
    rooms = cursor.fetchall()
    conn.close()
    if not rooms:
        return await callback.message.answer("Hozircha ochiq o'yin xonalari yo'q.")
    text = "🎮 **Ochiq o'yin xonalari:**\n\n"
    buttons = []
    for room_id, creator, bet in rooms:
        text += f"🏠 Xona #{room_id} | Tikilgan: {bet:,} EFC\n"
        buttons.append([InlineKeyboardButton(text=f"Qo'shilish #{room_id}", callback_data=f"match_join_{room_id}")])
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.answer(text, reply_markup=kb, parse_mode="Markdown")
@router.callback_query(F.data.startswith("match_join_"))
async def join_match(callback: CallbackQuery, state: FSMContext):
    room_id = int(callback.data.split("_")[-1])
    user_id = callback.from_user.id
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT creator_id, bet_efc, status FROM match_rooms WHERE room_id = ?", (room_id,))
    room = cursor.fetchone()
    if not room or room[2] != 'kutilmoqda':
        conn.close()
        return await callback.answer("Bu xona allaqachon to'lgan yoki yopilgan!", show_alert=True)
    creator_id, bet, _ = room
    cursor.execute("SELECT balans_efc FROM users WHERE user_id = ?", (user_id,))
    user_efc = cursor.fetchone()[0] or 0
    if user_efc < bet:
        conn.close()
        return await callback.answer(f"❌ Balansda mablag' yetarli emas! {bet:,} EFC kerak.", show_alert=True)
    cursor.execute("UPDATE users SET balans_efc = balans_efc - ? WHERE user_id = ?", (bet, user_id))
    cursor.execute("UPDATE match_rooms SET opponent_id = ?, status = 'o_yin' WHERE room_id = ?", (user_id, room_id))
    conn.commit()
    conn.close()
    await callback.message.delete()
    kb_opp = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="📸 Screenshot yuklash", callback_data=f"match_screen_{room_id}")]])
    await callback.message.answer(f"🎮 Siz #{room_id}-xonaga kirdingiz! Raqib bilan bog'laning.\nO'yin tugagach screenshot yuboring:", reply_markup=kb_opp)
    try:
        await callback.bot.send_message(chat_id=creator_id, text=f"🎮 Xona #{room_id} ga raqib kirdi! O'yin tugagach screenshot yuboring.", reply_markup=kb_opp)
    except: pass

@router.callback_query(F.data.startswith("match_screen_"))
async def start_screenshot(callback: CallbackQuery, state: FSMContext):
    room_id = int(callback.data.split("_")[-1])
    await state.update_data(room_id=room_id)
    await callback.message.answer("O'yin natijasi aks etgan skrinshotni (rasm shaklida) yuklang:")
    await state.set_state(MatchState.WAITING_FOR_SCREENSHOT)

@router.message(MatchState.WAITING_FOR_SCREENSHOT, F.photo)
async def process_screenshot(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    room_id = data['room_id']
    user_id = message.from_user.id
    username = f"@{message.from_user.username}" if message.from_user.username else f"ID: {user_id}"
    await state.clear()
    await message.answer("Rahmat! Screenshot kanalga yuborildi. Adminlar tekshirmoqda.")
    admin_kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🏆 Yaratuvchi g'olib", callback_data=f"win_c_{room_id}"),
        InlineKeyboardButton(text="🏆 Raqib g'olib", callback_data=f"win_o_{room_id}")
    ]])
    caption = f"📸 **Match #{room_id} Natijasi**\n\nYubordi: {username}\nAdmin g'olibni tasdiqlashi kutilmoqda."
    await bot.send_photo(chat_id=KANAL_ID, photo=message.photo[-1].file_id, caption=caption, reply_markup=admin_kb)

@router.callback_query(F.data.startswith("win_"))
async def admin_confirm_winner(callback: CallbackQuery, bot: Bot):
    if callback.from_user.id != ADMIN_ID:
        return await callback.answer("Siz admin emassiz!", show_alert=True)
    data_parts = callback.data.split("_")
    winner_type = data_parts[1]
    room_id = int(data_parts[2])
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT creator_id, opponent_id, bet_efc, status FROM match_rooms WHERE room_id = ?", (room_id,))
    room = cursor.fetchone()
    if not room or room[3] == 'yakunlandi':
        conn.close()
        return await callback.answer("Bu o'yin allaqachon hal qilingan!", show_alert=True)
    creator_id, opponent_id, bet, _ = room
    total_bank = bet * 2
    winner_prize = total_bank * (1 - MATCH_COMMISSION)
    if winner_type == "c":
        winner_id, loser_id, w_title = creator_id, opponent_id, "Xona yaratuvchisi"
    else:
        winner_id, loser_id, w_title = opponent_id, creator_id, "Raqib"
    cursor.execute("UPDATE users SET balans_efc = balans_efc + ? WHERE user_id = ?", (winner_prize, winner_id))
    cursor.execute("UPDATE match_rooms SET status = 'yakunlandi' WHERE room_id = ?", (room_id,))
    conn.commit()
    conn.close()
    await callback.message.edit_caption(caption=callback.message.caption + f"\n\n🟢 **G'OLIB TASDIQLANDI:** {w_title}")
    try: await bot.send_message(chat_id=winner_id, text=f"🥳 Tabriklaymiz! Hisobingizga {winner_prize:,} EFC o'tkazildi (15% komissiya chegirildi).")
    except: pass
    try: await bot.send_message(chat_id=loser_id, text=f"😞 Afsuski, #{room_id}-xonadagi o'yinda mag'lub bo'ldingiz.")
    except: pass
@router.message(F.text == "🎫 Oltin Bilet")
async def bilet_menu(message: Message):
    text = (
        f"🎫 **Oltin Bilet Bo'limi**\n\n"
        f"Jami biletlar soni: 64 ta.\n"
        f"ℹ️ *Bu biletni ishlatish siz uchun katta yangilik bo'ladi!*\n\n"
        f"Biletni sotib olgandan so'ng, uni P2P bo'limida o'zingiz xohlagan narxda qayta sotishingiz mumkin. "
        f"Biletlar P2P aylanmasida har ikki tomondan **{BILET_P2P_COMMISSION*100}%** komissiya olinadi."
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛒 Bilet sotib olish (Do'kon)", callback_data="ticket_shop_buy")],
        [InlineKeyboardButton(text="✨ Biletni ishlatish", callback_data="ticket_use")]
    ])
    await message.answer(text, reply_markup=kb, parse_mode="Markdown")

@router.callback_query(F.data == "ticket_shop_buy")
async def buy_ticket_from_shop(callback: CallbackQuery):
    user_id = callback.from_user.id
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM golden_tickets WHERE type = 'oltin'")
    count = cursor.fetchone()[0]
    if count >= 64:
        conn.close()
        return await callback.answer("❌ Afsuski barcha 64 ta Oltin bilet sotilib bo'lingan!", show_alert=True)
    cursor.execute("INSERT INTO golden_tickets (owner_id) VALUES (?)", (user_id,))
    conn.commit()
    conn.close()
    await callback.message.answer("🎉 Oltin biletni muvaffaqiyatli xarid qildingiz! Uni endi P2P birjasida qayta sotishingiz yoki saqlab turishingiz mumkin.")
    await callback.answer()

@router.callback_query(F.data == "ticket_use")
async def use_ticket(callback: CallbackQuery):
    user_id = callback.from_user.id
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT ticket_id FROM golden_tickets WHERE owner_id = ? AND status = 'aktiv' LIMIT 1", (user_id,))
    ticket = cursor.fetchone()
    if not ticket:
        conn.close()
        return await callback.answer("❌ Sizda faol Oltin bilet mavjud emas!", show_alert=True)
    cursor.execute("UPDATE golden_tickets SET status = 'ishlatildi' WHERE ticket_id = ?", (ticket[0],))
    conn.commit()
    conn.close()
    await callback.message.answer("🔥 **Bu biletni ishlatish siz uchun katta yangilik bo'ladi!**\n\n*(Biletlar oldi-sotti aylanmasidan keyin ma'lum vaqt o'tgach, biletlar orqali KATTA TURNIR e'lon qilinadi! Tizim tayyor.)*")
    await callback.answer()

@router.message(F.text == "⚙️ Admin Panel")
async def admin_panel(message: Message):
    if message.from_user.id != ADMIN_ID: return
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]
    conn.close()
    text = (
        f"⚙️ **Admin boshqaruv paneli**\n\n"
        f"👥 Umumiy a'zolar soni: {total_users} ta\n"
        f"🟢 Faol foydalanuvchilar: {total_users} ta\n\n"
        f"Admin ID: `{ADMIN_ID}`"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Turnir e'lon qilish (Hammaga xabar)", callback_data="admin_broadcast_tournament")]
    ])
    await message.answer(text, reply_markup=kb, parse_mode="Markdown")

@router.callback_query(F.data == "admin_broadcast_tournament")
async def start_broadcast(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID: return
    await callback.message.answer("Turnir haqida hammaga yuboriladigan e'lon matnini kiriting:")
    await state.set_state(AdminState.WAITING_FOR_BROADCAST)

@router.message(AdminState.WAITING_FOR_BROADCAST)
async def send_broadcast(message: Message, state: FSMContext, bot: Bot):
    if message.from_user.id != ADMIN_ID: return
    text_to_send = message.text
    await state.clear()
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users")
    users = cursor.fetchall()
    conn.close()
    count = 0
    for user in users:
        try:
            await bot.send_message(chat_id=user[0], text=f"🏆 **KATTA TURNIR E'LON QILINDI!** 🏆\n\n{text_to_send}")
            count += 1
        except: pass
    await message.answer(f"✅ Xabar {count} ta foydalanuvchiga muvaffaqiyatli tarqatildi va turnir rasman ochildi!")
