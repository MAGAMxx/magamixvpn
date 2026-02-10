"""
Модуль статистики админ панели
"""
import sqlite3
from datetime import datetime, timedelta
from aiogram import F, Router
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command

from config.settings import ADMIN_IDS

stats_router = Router()

# Фильтр только для админов
stats_router.message.filter(lambda message: message.from_user.id in ADMIN_IDS)
stats_router.callback_query.filter(lambda callback: callback.from_user.id in ADMIN_IDS)

@stats_router.callback_query(F.data == "admin_stats")
async def admin_stats(callback: CallbackQuery):
    """Детальная статистика"""
    conn = sqlite3.connect("database/data/users.db")
    c = conn.cursor()
    
    # Общая статистика
    c.execute("SELECT COUNT(*) FROM users")
    total_users = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM users WHERE got_free = 1")
    free_users = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM subscriptions WHERE status = 'active'")
    active_subs = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM payments WHERE status = 'pending'")
    pending_payments = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM reviews")
    total_reviews = c.fetchone()[0]
    
    # Статистика за сегодня
    today = datetime.now().strftime("%Y-%m-%d")
    c.execute("SELECT COUNT(*) FROM users WHERE reg_date LIKE ?", (f"{today}%",))
    today_users = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM subscriptions WHERE created_at LIKE ?", (f"{today}%",))
    today_subs = c.fetchone()[0]
    
    # Доходы
    c.execute("SELECT SUM(days * 5) FROM payments WHERE status = 'completed'")
    total_revenue = c.fetchone()[0] or 0
    
    conn.close()
    
    text = (
        f"📊 **Статистика бота**\n\n"
        f"**Общая статистика:**\n"
        f"👥 Всего пользователей: **{total_users}**\n"
        f"🎁 Получили бесплатные дни: **{free_users}**\n"
        f"✅ Активных подписок: **{active_subs}**\n"
        f"⏳ Ожидающих платежей: **{pending_payments}**\n"
        f"📝 Отзывов: **{total_reviews}**\n\n"
        f"**За сегодня:**\n"
        f"🆕 Новых пользователей: **{today_users}**\n"
        f"💳 Новых подписок: **{today_subs}**\n\n"
        f"💰 Примерный доход: **{total_revenue}₽**"
    )
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Обновить", callback_data="admin_stats")],
        [InlineKeyboardButton(text="📈 Детальная статистика", callback_data="admin_detailed_stats")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")]
    ])
    
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()

@stats_router.callback_query(F.data == "admin_detailed_stats")
async def admin_detailed_stats(callback: CallbackQuery):
    """Детальная статистика по дням"""
    conn = sqlite3.connect("database/data/users.db")
    c = conn.cursor()
    
    # Статистика за последние 7 дней
    stats_text = "📈 **Статистика за 7 дней:**\n\n"
    
    for i in range(7):
        date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
        
        c.execute("SELECT COUNT(*) FROM users WHERE reg_date LIKE ?", (f"{date}%",))
        day_users = c.fetchone()[0]
        
        c.execute("SELECT COUNT(*) FROM subscriptions WHERE created_at LIKE ?", (f"{date}%",))
        day_subs = c.fetchone()[0]
        
        day_name = (datetime.now() - timedelta(days=i)).strftime("%d.%m")
        stats_text += f"**{day_name}:** 👥{day_users} | 💳{day_subs}\n"
    
    conn.close()
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 К статистике", callback_data="admin_stats")]
    ])
    
    await callback.message.edit_text(stats_text, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()

@stats_router.callback_query(F.data == "admin_finance")
async def admin_finance(callback: CallbackQuery):
    """Финансовая статистика"""
    conn = sqlite3.connect("database/data/users.db")
    c = conn.cursor()
    
    # Статистика платежей
    c.execute("SELECT COUNT(*), SUM(days * 5) FROM payments WHERE status = 'completed'")
    completed_payments, total_revenue = c.fetchone()
    total_revenue = total_revenue or 0
    
    c.execute("SELECT COUNT(*) FROM payments WHERE status = 'pending'")
    pending_payments = c.fetchone()[0]
    
    # Статистика за месяц
    month_ago = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    c.execute("SELECT COUNT(*), SUM(days * 5) FROM payments WHERE created_at >= ? AND status = 'completed'", (month_ago,))
    month_payments, month_revenue = c.fetchone()
    month_revenue = month_revenue or 0
    
    conn.close()
    
    text = (
        f"💰 **Финансовая статистика**\n\n"
        f"**Всего:**\n"
        f"💳 Завершённых платежей: **{completed_payments}**\n"
        f"💰 Общий доход: **{total_revenue}₽**\n"
        f"⏳ Ожидающих платежей: **{pending_payments}**\n\n"
        f"**За месяц:**\n"
        f"💳 Платежей: **{month_payments}**\n"
        f"💰 Доход: **{month_revenue}₽**\n\n"
        f"📊 Средний чек: **{total_revenue // max(completed_payments, 1)}₽**"
    )
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Обновить", callback_data="admin_finance")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")]
    ])
    
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()

@stats_router.message(Command("stats"))
async def quick_stats(message: Message):
    """Быстрая статистика"""
    conn = sqlite3.connect("database/data/users.db")
    c = conn.cursor()
    
    c.execute("SELECT COUNT(*) FROM users")
    total_users = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM subscriptions WHERE status = 'active'")
    active_subs = c.fetchone()[0]
    
    today = datetime.now().strftime("%Y-%m-%d")
    c.execute("SELECT COUNT(*) FROM users WHERE reg_date LIKE ?", (f"{today}%",))
    today_users = c.fetchone()[0]
    
    conn.close()
    
    await message.answer(
        f"📊 **Быстрая статистика**\n\n"
        f"👥 Всего: {total_users}\n"
        f"✅ Активных: {active_subs}\n"
        f"🆕 Сегодня: {today_users}",
        parse_mode="Markdown"
    )

@stats_router.message(Command("backup"))
async def backup_database(message: Message):
    """Создание бэкапа базы данных"""
    import shutil
    import os
    
    try:
        backup_name = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        backup_path = f"database/data/{backup_name}"
        
        shutil.copy2("database/data/users.db", backup_path)
        
        await message.answer(
            f"✅ **Бэкап создан**\n\n"
            f"Файл: `{backup_name}`\n"
            f"Размер: {os.path.getsize(backup_path)} байт",
            parse_mode="Markdown"
        )
        
        # Отправляем файл админу
        with open(backup_path, 'rb') as backup_file:
            await message.answer_document(
                backup_file,
                caption="📁 Бэкап базы данных"
            )
            
    except Exception as e:
        await message.answer(f"❌ Ошибка создания бэкапа: {e}")

@stats_router.message(Command("logs"))
async def get_logs(message: Message):
    """Получение логов бота"""
    try:
        # Читаем последние 50 строк логов
        with open("bot.log", "r", encoding="utf-8") as log_file:
            lines = log_file.readlines()
            last_lines = lines[-50:] if len(lines) > 50 else lines
            
        log_text = "".join(last_lines)
        
        if len(log_text) > 4000:
            log_text = log_text[-4000:]
            log_text = "...\n" + log_text
        
        await message.answer(
            f"📋 **Последние логи:**\n\n```\n{log_text}\n```",
            parse_mode="Markdown"
        )
        
    except FileNotFoundError:
        await message.answer("❌ Файл логов не найден")
    except Exception as e:
        await message.answer(f"❌ Ошибка чтения логов: {e}")