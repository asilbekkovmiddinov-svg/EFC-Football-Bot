# handlers/p2p.py
import sqlite3
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from config import P2P_COMMISSION
from database import DB_NAME

router = Router()

class P2PState(StatesGroup):
    WAITING_FOR_EFC = State()
    WAITING_FOR_PRICE = State()

@router.message(F.text == "💱 P2P Birja")
async def p2p_menu(message: Message):
    text = (
        f"💱 **P2P Birja bo'limi**\n\n"
        f"Bu yerda siz mutlaqo xavfsiz va anonim tarzda virtual hamyonlar orqali EFC sotib olishingiz yoki sotishingiz mumkin.\n\n"
        f"⚠️ **Xavfsizlik qoidasi:**\n"
        f"Har bir muvaffaqiyatli savdo tranzaksiyasidan bot avtomatik ravishda xaridor va sotuvchidan **{P2P_COMMISSION*100}% dan** komissiya ushlab qoladi.\n"
        f"Barcha hisob-kitoblar bot tomonidan avtomatlashtirilgan."
    )
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛍 EFC Sotib olish (E'lonlar)", callback_data="p2p_buy_list")],
        [InlineKeyboardButton(text="📢 E'lon berish (Sotish)", callback_data="p2p_create_order")]
    ])
    await message.answer(text, reply_markup=kb, parse_mode="Markdown")

# E'lon berish boshlanishi
@router.callback_query(F.data == "p2p_create_order")
async def p2p_start_order(callback: CallbackQuery, state: FSMContext):
    await callback.message.delete()
    await callback.message.answer("Sotmoqchi bo'lgan EFC miqdorini kiriting:")
    await state.set_state(P2PState.WAITING_FOR_EFC)

# Miqdorni qabul qilish
@router.message(P2PState.WAITING_FOR_EFC)
async def p2p_process_efc(message: Message, state: FSMContext):
    try:
        efc_amount = float(message.text)
        if efc_amount <= 0:
            raise ValueError
    except ValueError:
        return await message.answer("Iltimos, to'g'ri va noldan katta miqdor kiriting:")
    
    # Sotuvchida yetarli EFC borligini tekshirish
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT balans_efc FROM users WHERE user_id = ?", (message.from_user.id,))
    user_efc = cursor.fetchone()[0]
    conn.close()
    
    if user_efc < efc_amount:
        await state.clear()
        return await message.answer(f"❌ Balansingizda yetarli EFC mavjud emas! Sizda bor: {user_efc:,} EFC")
        
    await state.update_data(efc_amount=efc_amount)
    await message.answer(f"Ushbu {efc_amount:,} EFC uchun umumiy qancha So'm olmoqchisiz? Narxni kiriting:")
    await state.set_state(P2PState.WAITING_FOR_PRICE)

# Narxni qabul qilish va e'lonni joylashtirish
@router.message(P2PState.WAITING_FOR_PRICE)
async def p2p_process_price(message: Message, state: FSMContext):
    try:
        som_price = float(message.text)
        if som_price <= 0:
            raise ValueError
    except ValueError:
        return await message.answer("Iltimos, narxni faqat raqamlarda va to'g'ri kiriting:")
        
    data = await state.get_data()
    efc_amount = data['efc_amount']
    seller_id = message.from_user.id
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # E'lon berilgan zahoti sotuvchining balansidan EFC muzlatiladi (ushlab turiladi)
    cursor.execute("UPDATE users SET balans_efc = balans_efc - ? WHERE user_id = ?", (efc_amount, seller_id))
    # E'lonni bazaga qo'shish
    cursor.execute("INSERT INTO p2p_orders (seller_id, efc_amount, som_price) VALUES (?, ?, ?)", (seller_id, efc_amount, som_price))
    conn.commit()
    conn.close()
    
    await state.clear()
    await message.answer(f"✅ E'loningiz muvaffaqiyatli joylashtirildi!\n💰 Miqdor: {efc_amount:,} EFC\n💵 Narxi: {som_price:,} so'm\nSavdo yakunlangach hisobingizga komissiya chegirilgan holda so'm kelib tushadi.")

# Faol e'lonlar ro'yxatini ko'rish
@router.callback_query(F.data == "p2p_buy_list")
async def p2p_show_list(callback: CallbackQuery):
    await callback.message.delete()
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT order_id, efc_amount, som_price FROM p2p_orders WHERE status = 'aktiv' AND seller_id != ?", (callback.from_user.id,))
    orders = cursor.fetchall()
    conn.close()
    
    if not orders:
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Orqaga", callback_data="p2p_back")]])
        return await callback.message.answer("Hozircha sotuvda faol e'lonlar yo'q.", reply_markup=kb)
        
    text = "🛒 **Sotuvdagi EFC e'lonlari ro'yxati:**\n\nSotib olmoqchi bo'lgan e'loningiz raqamini tanlang:\n"
    buttons = []
    
    for idx, (order_id, efc, som) in enumerate(orders, 1):
        text += f"{idx}. #{order_id} buyurtma: {efc:,} EFC ➡️ {som:,} so'm\n"
        buttons.append([InlineKeyboardButton(text=f"Sotib olish #{order_id}", callback_data=f"p2p_buy_{order_id}")])
        
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.answer(text, reply_markup=kb, parse_mode="Markdown")

# P2P sotib olishni amalga oshirish va 2.5% + 2.5% komissiyani hisoblash
@router.callback_query(F.data.startswith("p2p_buy_"))
async def p2p_execute_deal(callback: CallbackQuery):
    order_id = int(callback.data.split("_")[-1])
    buyer_id = callback.from_user.id
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # E'lon ma'lumotlarini olish
    cursor.execute("SELECT seller_id, efc_amount, som_price, status FROM p2p_orders WHERE order_id = ?", (order_id,))
    order = cursor.fetchone()
    
    if not order or order[3] != 'aktiv':
        conn.close()
        return await callback.answer("Bu e'lon allaqachon sotilgan yoki o'chirilgan!", show_alert=True)
        
    seller_id, efc_amount, som_price, _ = order
    
    # Xaridorning so'm balansini tekshirish
    cursor.execute("SELECT balans_som FROM users WHERE user_id = ?", (buyer_id,))
    buyer_som = cursor.fetchone()[0]
    
    if buyer_som < som_price:
        conn.close()
        return await callback.answer(f"❌ Balansingizda mablag' yetarli emas! Sizga {som_price:,} so'm kerak.", show_alert=True)
        
    # Avtomatik komissiya hisob kitobi
    # 1. Sotuvchiga tushadigan so'mdan 2.5% ushlanadi
    seller_takes_som = som_price * (1 - P2P_COMMISSION)
    # 2. Xaridorga tushadigan EFC dan 2.5% ushlanadi
    buyer_takes_efc = efc_amount * (1 - P2P_COMMISSION)
    
    # Pul o'tkazmalarini avtomatik bajarish
    # Xaridordan so'mni yechish
    cursor.execute("UPDATE users SET balans_som = balans_som - ? WHERE user_id = ?", (som_price, buyer_id))
    # Xaridorga komissiya chegirilgan EFC ni berish
    cursor.execute("UPDATE users SET balans_efc = balans_efc + ? WHERE user_id = ?", (buyer_takes_efc, buyer_id))
    
    # Sotuvchiga komissiya chegirilgan So'mni berish (EFCsi allaqachon e'lon berganda yechilgan edi)
    cursor.execute("UPDATE users SET balans_som = balans_som + ? WHERE user_id = ?", (seller_takes_som, seller_id))
    
    # E'lon holatini yangilash
    cursor.execute("UPDATE p2p_orders SET status = 'yakunlandi' WHERE order_id = ?", (order_id,))
    
    conn.commit()
    conn.close()
    
    await callback.message.delete()
    await callback.message.answer(
        f"🎉 **Savdo muvaffaqiyatli yakunlandi!**\n\n"
        f"Siz sotib oldingiz: {buyer_takes_efc:,} EFC (2.5% komissiya ushlandi)\n"
        f"Balansingizdan yechildi: {som_price:,} so'm"
    )
    
    # Sotuvchiga botdan avtomatik xabar yuborish
    try:
        await callback.bot.send_message(
            chat_id=seller_id,
            text=f"💰 **P2P Birja: E'loningiz sotildi!**\n\n"
                 f"Sizning #{order_id} e'loningiz xaridor tomonidan sotib olindi.\n"
                 f"Hisobingizga o'tkazildi: {seller_takes_som:,} so'm (2.5% komissiya ushlandi)."
        )
    except Exception:
        pass
        
    await callback.answer()
  
