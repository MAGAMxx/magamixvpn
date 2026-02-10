"""
Модуль управления пользователями
"""
import sqlite3
from aiogram import F, Router
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config.settings import ADMIN_IDS
from services.hiddify_service import HiddifyService

users_router = Router()
hiddify_service = HiddifyService()

# Фильтр только для админов
users_router.message.filter(lambda message: message.from_user.id in ADMIN_IDS)
users_router.callback_query.filter(lambda callback: callback.from_user.id in ADMIN_IDS)

class UserStates(StatesGroup):
    waiting_user_id = State()
    waiting_days_to_add = State()
    waiting_user_search = State()

@users_router.callback_query(F.data == "admin_users")
async def admin_users(callback: CallbackQuery):
    """Управление пользователями"""
    text = (
        "👥 **Управление пользователями**\n\n"
        "Выберите действие:"
    )
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить дни пользователю", callback_data="admin_add_days")],
        [InlineKeyboardButton(text="🔎 Найтил пользователя", callback_data="admin_find_user")],
        [InlineKeyboardButton(text="💰 Топ покупателей", callback_data="admin_top_users")],
        [InlineKeyboardButton(text="🚫 Заблокировать пользователя", callback_data="admin_ban_user")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")]
    ])
    
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()

@users_router.callback_query(F.data == "admin_add_days")
async def admin_add_days(callback: CallbackQuery, state: FSMContext):
    """Добавить дни пользователю"""
    text = "➕ **Добавить дни пользователю**\n\nВведите ID пользователя:"
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_users")]
    ])
    
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    await state.set_state(UserStates.waiting_user_id)
    await callback.answer()

@users_router.message(UserStates.waiting_user_id)
async def process_user_id(message: Message, state: FSMContext):
    """Обработка ID пользователя"""
    try:
        user_id = int(message.text)
        await state.update_data(target_user_id=user_id)
        
        await message.answer(
            f"👤 **Пользователь:** {user_id}\n\n"
            "Введите количество дней для добавления:",
            parse_mode="Markdown"
        )
        await state.set_state(UserStates.waiting_days_to_add)
        
    except ValueError:
        await message.answer("❌ Неверный формат ID. Введите число.")

@users_router.message(UserStates.waiting_days_to_add)
async def process_days_to_add(message: Message, state: FSMContext):
    """Обработка количества дней"""
    try:
        days = int(message.text)
        data = await state.get_data()
        target_user_id = data["target_user_id"]
        
        # Добавляем дни
        from database.models import get_latest_subscription
        existing_uuid = get_latest_subscription(target_user_id)
        
        if existing_uuid:
            result = hiddify_service.create_or_extend_both(
                added_days=days,
                user_id=target_user_id,
                existing_uuid=existing_uuid
            )
        else:
            result = hiddify_service.create_or_extend_both(
                added_days=days,
                user_id=target_user_id
            )
        
        if result:
            await message.answer(
                f"✅ **Успешно!**\n\n"
                f"Пользователю {target_user_id} добавлено {days} дней",
                parse_mode="Markdown"
            )
            
            # Уведомляем пользователя
            try:
                await message.bot.send_message(
                    target_user_id,
                    f"🎁 **Подарок от администрации!**\n\n"
                    f"Вам добавлено **{days} дней** VPN!\n"
                    f"Спасибо за использование нашего сервиса! 💙",
                    parse_mode="Markdown"
                )
            except:
                pass
        else:
            await message.answer("❌ Ошибка при добавлении дней")
        
        await state.clear()
        
    except ValueError:
        await message.answer("❌ Неверный формат. Введите число дней.")

@users_router.callback_query(F.data == "admin_find_user")
async def admin_find_user(callback: CallbackQuery, state: FSMContext):
    """Поиск пользователя"""
    text = (
        "🔍 **Поиск пользователя**\n\n"
        "Введите ID пользователя или username:"
    )
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_users")]
    ])
    
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    await state.set_state(UserStates.waiting_user_search)
    await callback.answer()

@users_router.message(UserStates.waiting_user_search)
async def process_user_search(message: Message, state: FSMContext):
    """Обработка поиска пользователя"""
    from database.models import search_user, get_user_subscriptions
    
    query = message.text.strip()
    user_data = search_user(query)
    
    if user_data:
        user_id, username, reg_date, got_free = user_data
        subs = get_user_subscriptions(user_id)
        
        text = (
            f"👤 **Информация о пользователе**\n\n"
            f"**ID:** {user_id}\n"
            f"**Username:** @{username or 'нет'}\n"
            f"**Дата регистрации:** {reg_date}\n"
            f"**Получал бесплатные дни:** {'Да' if got_free else 'Нет'}\n"
            f"**Активных подписок:** {len(subs)}\n\n"
        )
        
        if subs:
            text += "**Подписки:**\n"
            for uuid, created_at in subs:
                remaining = hiddify_service.get_remaining_days(uuid)
                text += f"• {uuid[:8]}... ({remaining} дней)\n"
        
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➕ Добавить дни", callback_data=f"admin_add_days_{user_id}")],
            [InlineKeyboardButton(text="� Детали,", callback_data=f"admin_user_details_{user_id}")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_users")]
        ])
        
        await message.answer(text, reply_markup=kb, parse_mode="Markdown")
    else:
        await message.answer("❌ Пользователь не найден")
    
    await state.clear()

@users_router.callback_query(F.data == "admin_top_users")
async def admin_top_users(callback: CallbackQuery):
    """Топ пользователи по платежам"""
    conn = sqlite3.connect("database/data/users.db")
    c = conn.cursor()
    
    # Топ пользователи по количеству платежей
    c.execute("""
        SELECT u.user_id, u.username, COUNT(p.id) as payment_count, SUM(p.days * 5) as total_spent
        FROM users u 
        LEFT JOIN payments p ON u.user_id = p.user_id AND p.status = 'completed'
        GROUP BY u.user_id, u.username
        HAVING payment_count > 0
        ORDER BY payment_count DESC, total_spent DESC
        LIMIT 10
    """)
    top_users = c.fetchall()
    
    conn.close()
    
    text = "💰 **Топ пользователи по платежам:**\n\n"
    
    if not top_users:
        text += "Пока нет пользователей с завершенными платежами"
    else:
        for i, (user_id, username, payment_count, total_spent) in enumerate(top_users, 1):
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            username_display = f"@{username}" if username else f"ID:{user_id}"
            total_spent = total_spent or 0
            text += f"{medal} {username_display} - {payment_count} платежей ({total_spent}₽)\n"
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Обновить", callback_data="admin_top_users")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_users")]
    ])
    
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()

@users_router.callback_query(F.data == "admin_ban_user")
async def admin_ban_user(callback: CallbackQuery):
    """Заблокировать пользователя (заглушка)"""
    text = (
        "🚫 **Блокировка пользователей**\n\n"
        "Функция в разработке.\n"
        "Используйте команду /ban <user_id> для блокировки."
    )
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_users")]
    ])
    
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()