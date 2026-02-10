"""
Модуль рассылки сообщений
"""
import sqlite3
from aiogram import F, Router
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config.settings import ADMIN_IDS

broadcast_router = Router()

# Фильтр только для админов
broadcast_router.message.filter(lambda message: message.from_user.id in ADMIN_IDS)
broadcast_router.callback_query.filter(lambda callback: callback.from_user.id in ADMIN_IDS)

class BroadcastStates(StatesGroup):
    waiting_broadcast = State()

@broadcast_router.callback_query(F.data == "admin_broadcast")
async def admin_broadcast(callback: CallbackQuery, state: FSMContext):
    """Рассылка"""
    text = (
        "📤 **Рассылка сообщений**\n\n"
        "Введите текст для рассылки всем пользователям:"
    )
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")]
    ])
    
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    await state.set_state(BroadcastStates.waiting_broadcast)
    await callback.answer()

@broadcast_router.message(BroadcastStates.waiting_broadcast)
async def process_broadcast(message: Message, state: FSMContext):
    """Обработка рассылки"""
    broadcast_text = message.text
    
    conn = sqlite3.connect("database/data/users.db")
    c = conn.cursor()
    c.execute("SELECT user_id FROM users")
    user_ids = [row[0] for row in c.fetchall()]
    conn.close()
    
    sent = 0
    failed = 0
    
    progress_msg = await message.answer("📤 **Рассылка началась...**", parse_mode="Markdown")
    
    for i, user_id in enumerate(user_ids):
        try:
            await message.bot.send_message(user_id, broadcast_text, parse_mode="Markdown")
            sent += 1
        except:
            failed += 1
        
        # Обновляем прогресс каждые 50 сообщений
        if i % 50 == 0:
            await progress_msg.edit_text(
                f"📤 **Рассылка в процессе...**\n\n"
                f"Отправлено: {sent}\n"
                f"Не удалось: {failed}\n"
                f"Прогресс: {i}/{len(user_ids)}",
                parse_mode="Markdown"
            )
    
    await progress_msg.edit_text(
        f"📤 **Рассылка завершена**\n\n"
        f"✅ Отправлено: {sent}\n"
        f"❌ Не удалось: {failed}",
        parse_mode="Markdown"
    )
    
    await state.clear()