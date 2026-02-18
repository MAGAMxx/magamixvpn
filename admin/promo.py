"""
Модуль управления промокодами
"""
import sqlite3
from aiogram import F, Router
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config.settings import ADMIN_IDS
from config.payments import PROMO_CODES

promo_router = Router()

promo_router.callback_query.filter(lambda callback: callback.from_user.id in ADMIN_IDS)
promo_router.message.filter(lambda message: message.from_user.id in ADMIN_IDS)

class PromoStates(StatesGroup):
    waiting_promo_name = State()
    waiting_promo_discount = State()
    waiting_edit_name = State()
    waiting_edit_discount = State()

def init_promo_db():
    conn = sqlite3.connect("database/data/users.db")
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS promo_usage (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        promo_code TEXT,
        user_id INTEGER,
        used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        discount_amount INTEGER
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS promo_codes (
        code TEXT PRIMARY KEY,
        discount INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        is_active INTEGER DEFAULT 1
    )''')
    
    for code, discount in PROMO_CODES.items():
        c.execute("INSERT OR IGNORE INTO promo_codes (code, discount) VALUES (?, ?)", 
                 (code, discount))
    
    conn.commit()
    conn.close()

def get_active_promo_codes():
    conn = sqlite3.connect("database/data/users.db")
    c = conn.cursor()
    c.execute("SELECT code, discount FROM promo_codes WHERE is_active = 1")
    codes = dict(c.fetchall())
    conn.close()
    return codes

def add_promo_code(code, discount):
    conn = sqlite3.connect("database/data/users.db")
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO promo_codes (code, discount) VALUES (?, ?)", 
             (code, discount))
    conn.commit()
    conn.close()

def delete_promo_code(code):
    conn = sqlite3.connect("database/data/users.db")
    c = conn.cursor()
    c.execute("UPDATE promo_codes SET is_active = 0 WHERE code = ?", (code,))
    conn.commit()
    conn.close()

def update_promo_code(old_code, new_code, discount):
    conn = sqlite3.connect("database/data/users.db")
    c = conn.cursor()
    if old_code != new_code:
        c.execute("UPDATE promo_codes SET is_active = 0 WHERE code = ?", (old_code,))
        c.execute("INSERT OR REPLACE INTO promo_codes (code, discount) VALUES (?, ?)", 
                 (new_code, discount))
    else:
        c.execute("UPDATE promo_codes SET discount = ? WHERE code = ?", 
                 (discount, old_code))
    conn.commit()
    conn.close()

init_promo_db()

@promo_router.callback_query(F.data == "admin_promo")
async def admin_promo(callback: CallbackQuery):
    promo_codes = get_active_promo_codes()
    
    if not promo_codes:
        text = "🎫 **Промокоды**\n\nАктивных промокодов нет"
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➕ Создать промокод", callback_data="admin_create_promo")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")]
        ])
    else:
        text = "🎫 **Промокоды**\n\nВыберите промокод для управления:"
        
        buttons = []
        for code, discount in promo_codes.items():
            buttons.append([
                InlineKeyboardButton(text=f"{code} {discount}%", callback_data=f"promo_manage_{code}"),
                InlineKeyboardButton(text="🗑️", callback_data=f"promo_del_{code}")
            ])
        
        buttons.append([InlineKeyboardButton(text="➕ Создать промокод", callback_data="admin_create_promo")])
        buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")])
        
        kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()

@promo_router.callback_query(F.data.startswith("promo_manage_"))
async def promo_manage(callback: CallbackQuery):
    promo_code = callback.data.replace("promo_manage_", "")
    promo_codes = get_active_promo_codes()
    
    if promo_code not in promo_codes:
        await callback.answer("❌ Промокод не найден")
        return
    
    conn = sqlite3.connect("database/data/users.db")
    c = conn.cursor()
    
    c.execute("SELECT COUNT(*) FROM promo_usage WHERE promo_code = ?", (promo_code,))
    usage_count = c.fetchone()[0]
    
    c.execute("SELECT SUM(discount_amount) FROM promo_usage WHERE promo_code = ?", (promo_code,))
    total_discount = c.fetchone()[0] or 0
    
    c.execute("""SELECT user_id, used_at FROM promo_usage 
                 WHERE promo_code = ? ORDER BY used_at DESC LIMIT 5""", (promo_code,))
    recent_usage = c.fetchall()
    
    conn.close()
    
    text = (
        f"🎫 **Промокод: {promo_code}**\n\n"
        f"💰 Скидка: **{promo_codes[promo_code]}%**\n"
        f"📊 Использований: **{usage_count}**\n"
        f"💸 Общая скидка: **{total_discount}₽**\n\n"
    )
    
    if recent_usage:
        text += "**Последние использования:**\n"
        for user_id, used_at in recent_usage:
            text += f"• Пользователь {user_id} - {used_at[:16]}\n"
    else:
        text += "Промокод еще не использовался"
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Изменить название", callback_data=f"promo_edit_name_{promo_code}")],
        [InlineKeyboardButton(text="💰 Изменить скидку", callback_data=f"promo_edit_discount_{promo_code}")],
        [InlineKeyboardButton(text="🗑️ Удалить промокод", callback_data=f"promo_del_{promo_code}")],
        [InlineKeyboardButton(text="🔙 К промокодам", callback_data="admin_promo")]
    ])
    
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()

@promo_router.callback_query(F.data.startswith("promo_del_"))
async def promo_delete_ask(callback: CallbackQuery, state: FSMContext):
    promo_code = callback.data.replace("promo_del_", "")
    
    await state.update_data(promo_to_delete=promo_code)
    
    text = f"🗑️ **Удаление промокода**\n\nВы уверены, что хотите удалить промокод **{promo_code}**?"
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Да, удалить", callback_data="promo_confirm_delete")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_promo")]
    ])
    
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()

@promo_router.callback_query(F.data == "promo_confirm_delete")
async def promo_delete_execute(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    promo_code = data.get("promo_to_delete")
    
    if promo_code:
        delete_promo_code(promo_code)
        await callback.answer("✅ Промокод удален!")
        await state.clear()
        await admin_promo(callback)
    else:
        await callback.answer("❌ Ошибка удаления")
        await admin_promo(callback)

@promo_router.callback_query(F.data == "admin_create_promo")
async def admin_create_promo(callback: CallbackQuery, state: FSMContext):
    text = "➕ **Создание промокода**\n\nВведите название промокода:"
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_promo")]
    ])
    
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    await state.set_state(PromoStates.waiting_promo_name)
    await callback.answer()

@promo_router.message(PromoStates.waiting_promo_name)
async def process_promo_name(message: Message, state: FSMContext):
    promo_name = message.text.strip().upper()
    promo_codes = get_active_promo_codes()
    
    if promo_name in promo_codes:
        await message.answer("❌ Промокод с таким названием уже существует!")
        return
    
    if len(promo_name) < 3 or len(promo_name) > 20:
        await message.answer("❌ Название должно быть от 3 до 20 символов!")
        return
    
    await state.update_data(promo_name=promo_name)
    await message.answer(
        f"✅ Название: **{promo_name}**\n\nТеперь введите размер скидки (от 1 до 50%):",
        parse_mode="Markdown"
    )
    await state.set_state(PromoStates.waiting_promo_discount)

@promo_router.message(PromoStates.waiting_promo_discount)
async def process_promo_discount(message: Message, state: FSMContext):
    try:
        discount = int(message.text.strip())
        
        if discount < 1 or discount > 50:
            await message.answer("❌ Скидка должна быть от 1 до 50%!")
            return
        
        data = await state.get_data()
        promo_name = data["promo_name"]
        
        add_promo_code(promo_name, discount)
        
        await message.answer(
            f"✅ **Промокод создан!**\n\n"
            f"🎫 Название: **{promo_name}**\n"
            f"💰 Скидка: **{discount}%**",
            parse_mode="Markdown"
        )
        
        await state.clear()
        
    except ValueError:
        await message.answer("❌ Введите число от 1 до 50!")

@promo_router.callback_query(F.data.startswith("promo_edit_name_"))
async def promo_edit_name(callback: CallbackQuery, state: FSMContext):
    promo_code = callback.data.replace("promo_edit_name_", "")
    
    await state.update_data(old_promo_name=promo_code)
    
    text = f"✏️ **Изменение названия**\n\nТекущее название: **{promo_code}**\nВведите новое название:"
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data=f"promo_manage_{promo_code}")]
    ])
    
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    await state.set_state(PromoStates.waiting_edit_name)
    await callback.answer()

@promo_router.message(PromoStates.waiting_edit_name)
async def process_edit_name(message: Message, state: FSMContext):
    new_name = message.text.strip().upper()
    data = await state.get_data()
    old_name = data["old_promo_name"]
    promo_codes = get_active_promo_codes()
    
    if new_name in promo_codes and new_name != old_name:
        await message.answer("❌ Промокод с таким названием уже существует!")
        return
    
    if len(new_name) < 3 or len(new_name) > 20:
        await message.answer("❌ Название должно быть от 3 до 20 символов!")
        return
    
    old_discount = promo_codes[old_name]
    update_promo_code(old_name, new_name, old_discount)
    
    await message.answer(
        f"✅ **Название изменено!**\n\n"
        f"Было: **{old_name}**\n"
        f"Стало: **{new_name}**",
        parse_mode="Markdown"
    )
    
    await state.clear()

@promo_router.callback_query(F.data.startswith("promo_edit_discount_"))
async def promo_edit_discount(callback: CallbackQuery, state: FSMContext):
    promo_code = callback.data.replace("promo_edit_discount_", "")
    promo_codes = get_active_promo_codes()
    
    await state.update_data(promo_name=promo_code)
    
    text = (
        f"💰 **Изменение скидки**\n\n"
        f"Промокод: **{promo_code}**\n"
        f"Текущая скидка: **{promo_codes[promo_code]}%**\n\n"
        f"Введите новую скидку (от 1 до 50%):"
    )
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data=f"promo_manage_{promo_code}")]
    ])
    
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    await state.set_state(PromoStates.waiting_edit_discount)
    await callback.answer()

@promo_router.message(PromoStates.waiting_edit_discount)
async def process_edit_discount(message: Message, state: FSMContext):
    try:
        new_discount = int(message.text.strip())
        
        if new_discount < 1 or new_discount > 50:
            await message.answer("❌ Скидка должна быть от 1 до 50%!")
            return
        
        data = await state.get_data()
        promo_name = data["promo_name"]
        promo_codes = get_active_promo_codes()
        old_discount = promo_codes[promo_name]
        
        update_promo_code(promo_name, promo_name, new_discount)
        
        await message.answer(
            f"✅ **Скидка изменена!**\n\n"
            f"Промокод: **{promo_name}**\n"
            f"Было: **{old_discount}%**\n"
            f"Стало: **{new_discount}%**",
            parse_mode="Markdown"
        )
        
        await state.clear()
        
    except ValueError:
        await message.answer("❌ Введите число от 1 до 50!")
