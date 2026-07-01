# handlers/wallet.py
import sqlite3
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from config import ADMIN_ID, KARTA_RAQAM, KARTA_EGA_SI
from database import DB_NAME

router = Router()

class DepositState(StatesGroup):
    WAITING_FOR_AMOUNT = State()
    WAITING_FOR_CHEQUE = State()

# Hamyon menyusi
@router.message(F.text == "🧳 Balans va Hamyon")
async def wallet_menu(message: Message):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT balans_som, balans_efc, balans_coin FROM users WHERE user_id = ?", (message.from_user.id,))
    user = cursor.fetchone()
    
    if not user:
        cursor.execute("INSERT INTO users (user_id, username) VALUES (?, ?)", (message.from_user.id, message.from_user.username))
        conn.commit()
        user = (0, 0, 0)
    conn.close()

    text = (
        f"📊 **Sizning hamyoningiz:**\n\n"
        f"💰 Balans: {user[0]:,} so'm\n"
        f"🪙 EFC: {user[1]:,} efc\n"
        f"💎 Coin: {user[2]:,} coin\n\n"
        f"Faqat balansga so'm kiritish va yechish mumkin."
    )
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📥 So'm kiritish", callback_data="deposit_som")],
        [InlineKeyboardButton(text="📤 So'm yechish", callback_data="withdraw_som")]
    ])
    await message.answer(text, reply_markup=kb, parse_mode="Markdown")

# So'm kiritish boshlanishi
@router.callback_query(F.data == "deposit_som")
async def start_deposit(callback: CallbackQuery, state: FSMContext):
    await callback.message.delete()
    await callback.message.answer("Qancha so'm kiritmoqchisiz? Miqdorini raqamlarda kiriting:")
    await state.set_state(DepositState.WAITING_FOR_AMOUNT)

# Miqdor qabul qilish
@router.message(DepositState.WAITING_FOR_AMOUNT)
async def process_amount(message: Message, state: FSMContext):
    if not message.text.isdigit():
        return await message.answer("Iltimos, faqat raqamlarda miqdor kiriting:")
    
    amount = float(message.text)
    await state.update_data(amount=amount)
    
    text = (
        f"💳 **To'lov ma'lumotlari:**\n\n"
        f"Karta raqam: `{KARTA_RAQAM}`\n"
        f"Ega si: {KARTA_EGA_SI}\n"
        f"Siz o'tkazadigan miqdor: {amount:,} so'm\n\n"
        f"To'lovni amalga oshirib, chekni (rasm shaklida) shu yerga yuboring."
    )
    await message.answer(text, parse_mode="Markdown")
    await state.set_state(DepositState.WAITING_FOR_CHEQUE)

# Chek qabul qilish va adminga yuborish
@router.message(DepositState.WAITING_FOR_CHEQUE, F.photo)
async def process_cheque(message: Message, state: FSMContext, bot: Bot):
    user_data = await state.get_data()
    amount = user_data['amount']
    user_id = message.from_user.id
    username = f"@{message.from_user.username}" if message.from_user.username else f"ID: {user_id} (Username yo'q)"
    
    # Bazaga buyurtmani saqlash
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO deposit_orders (user_id, amount) VALUES (?, ?)", (user_id, amount))
    order_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    await state.clear()
    await message.answer("Sizning chekingiz adminga yuborildi. Tekshirilmoqda, iltimos kuting...")
    
    # Adminga yuborish paneli
    admin_text = (
        f"📦 **Yangi buyurtma #{order_id}**\n\n"
        f"👤 Mijoz: {username}\n"
        f"🆔 Mijoz ID: {user_id}\n"
        f"💰 Miqdor: {amount:,} so'm\n"
    )
    
    admin_kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Qabul qilish", callback_data=f"accept_{order_id}"),
            InlineKeyboardButton(text="❌ Rad etish", callback_data=f"reject_{order_id}")
        ]
    ])
    
    # Eng oxirgi rasmni (eng sifatlisini) adminga jo'natamiz
    await bot.send_photo(chat_id=ADMIN_ID, photo=message.photo[-1].file_id, caption=admin_text, reply_markup=admin_kb)

# Admin: Qabul qilish yoki Rad etish
@router.callback_query(F.data.startswith("accept_") | F.data.startswith("reject_"))
async def handle_admin_decision(callback: CallbackQuery, bot: Bot):
    action, order_id = callback.data.split("_")
    order_id = int(order_id)
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, amount, status FROM deposit_orders WHERE order_id = ?", (order_id,))
    order = cursor.fetchone()
    
    if not order or order[2] != 'kutilmoqda':
        conn.close()
        return await callback.answer("Bu buyurtma allaqachon ko'rib chiqilgan!", show_alert=True)
    
    user_id, amount, _ = order
    
    if action == "accept":
        # Balansni to'ldirish
        cursor.execute("UPDATE users SET balans_som = balans_som + ? WHERE user_id = ?", (amount, user_id))
        cursor.execute("UPDATE deposit_orders SET status = 'tasdiqlandi' WHERE order_id = ?", (order_id,))
        conn.commit()
        
        await callback.message.edit_caption(caption=callback.message.caption + "\n\n🟢 **STATUS: QABUL QILINDI**")
        await bot.send_message(chat_id=user_id, text="✅ Buyurtma bajarildi! Balansingiz to'ldirildi.")
        
    elif action == "reject":
        cursor.execute("UPDATE deposit_orders SET status = 'rad_etildi' WHERE order_id = ?", (order_id,))
        conn.commit()
        
        await callback.message.edit_caption(caption=callback.message.caption + "\n\n🔴 **STATUS: RAD ETILDI**")
        await bot.send_message(chat_id=user_id, text="❌ Buyurtma rad etildi. Muammo bo'yicha admin bilan bog'laning.")
        
    conn.close()
    await callback.answer()
  
