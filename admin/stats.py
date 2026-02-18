import sqlite3
from datetime import datetime, timedelta
from aiogram import F, Router
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command

from config.settings import ADMIN_IDS

stats_router = Router()

stats_router.message.filter(lambda message: message.from_user.id in ADMIN_IDS)
stats_router.callback_query.filter(lambda callback: callback.from_user.id in ADMIN_IDS)

@stats_router.callback_query(F.data == "admin_stats")
async def admin_stats(callback: CallbackQuery):
    conn = sqlite3.connect("database/data/users.db")
    c = conn.cursor()

    c.execute("SELECT COUNT(*) FROM users")
    total_users = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM users WHERE got_free = 1")
    free_users = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM subscriptions WHERE status = 'active'")
    active_subs = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM payments WHERE status = 'pending'")
    pending_payments = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM payments WHERE status = 'completed'")
    completed_payments = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM reviews")
    total_reviews = c.fetchone()[0]

    today = datetime.now().strftime("%Y-%m-%d")
    c.execute("SELECT COUNT(*) FROM users WHERE reg_date LIKE ?", (f"{today}%",))
    today_users = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM subscriptions WHERE created_at LIKE ?", (f"{today}%",))
    today_subs = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM payments WHERE status = 'completed' AND created_at LIKE ?", (f"{today}%",))
    today_payments = c.fetchone()[0]

    conn.close()

    conversion = (active_subs / max(total_users, 1)) * 100

    text = (
        f"📊 **СТАТИСТИКА**\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"```\n"
        f"Показатель     |  Кол-во\n"
        f"---------------|--------\n"
        f"👥 Всего юзеров |  {total_users:>5}\n"
        f"🎁 Бесплатных   |  {free_users:>5}\n"
        f"✅ Актив. подп.  |  {active_subs:>5}\n"
        f"📈 Конверсия    | {conversion:>5.1f}%\n"
        f"---------------|--------\n"
        f"💳 Усп. платежи |  {completed_payments:>5}\n"
        f"⏳ Ожидающие    |  {pending_payments:>5}\n"
        f"📝 Отзывы       |  {total_reviews:>5}\n"
        f"---------------|--------\n"
        f"📅 СЕГОДНЯ      |       \n"
        f"  Юзеры        |  {today_users:>5}\n"
        f"  Подписки     |  {today_subs:>5}\n"
        f"  Платежи      |  {today_payments:>5}\n"
        f"```"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📈 По дням (7 дней)", callback_data="admin_detailed_stats")],
        [InlineKeyboardButton(text="🔄 Обновить", callback_data="admin_stats")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")]
    ])

    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()

@stats_router.callback_query(F.data == "admin_detailed_stats")
async def admin_detailed_stats(callback: CallbackQuery):
    conn = sqlite3.connect("database/data/users.db")
    c = conn.cursor()

    text = "📈 **СТАТИСТИКА ЗА 7 ДНЕЙ**\n━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    text += "```\n"
    text += "Дата       | Юзеры | Подписки\n"
    text += "-----------|-------|--------\n"

    total_users_week = 0
    total_subs_week = 0

    for i in range(6, -1, -1):
        date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
        day_name = (datetime.now() - timedelta(days=i)).strftime("%d.%m")

        c.execute("SELECT COUNT(*) FROM users WHERE reg_date LIKE ?", (f"{date}%",))
        day_users = c.fetchone()[0]

        c.execute("SELECT COUNT(*) FROM subscriptions WHERE created_at LIKE ?", (f"{date}%",))
        day_subs = c.fetchone()[0]

        total_users_week += day_users
        total_subs_week += day_subs

        today_mark = " ◀" if i == 0 else ""
        text += f"{day_name}      |   {day_users:>3} |   {day_subs:>3}{today_mark}\n"

    text += f"-----------|-------|--------\n"
    text += f"ИТОГО      |   {total_users_week:>3} |   {total_subs_week:>3}\n"
    text += "```"

    conn.close()

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 К статистике", callback_data="admin_stats")]
    ])

    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()

@stats_router.callback_query(F.data == "admin_finance")
async def admin_finance(callback: CallbackQuery):
    conn = sqlite3.connect("database/data/users.db")
    c = conn.cursor()

    c.execute("SELECT COUNT(*) FROM payments WHERE status = 'completed'")
    completed_payments = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM payments WHERE status = 'pending'")
    pending_payments = c.fetchone()[0]

    today = datetime.now().strftime("%Y-%m-%d")
    c.execute("SELECT COUNT(*) FROM payments WHERE status = 'completed' AND created_at LIKE ?", (f"{today}%",))
    today_payments = c.fetchone()[0]

    month_ago = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    c.execute("SELECT COUNT(*) FROM payments WHERE created_at >= ? AND status = 'completed'", (month_ago,))
    month_payments = c.fetchone()[0]

    week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    c.execute("SELECT COUNT(*) FROM payments WHERE created_at >= ? AND status = 'completed'", (week_ago,))
    week_payments = c.fetchone()[0]

    c.execute("SELECT tarif, COUNT(*) as cnt FROM payments WHERE status = 'completed' GROUP BY tarif ORDER BY cnt DESC LIMIT 5")
    popular_tarifs = c.fetchall()

    conn.close()

    text = (
        f"💰 **ФИНАНСЫ**\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"```\n"
        f"Показатель     |  Кол-во\n"
        f"---------------|--------\n"
        f"✅ Успешных     |  {completed_payments:>5}\n"
        f"⏳ Ожидающих    |  {pending_payments:>5}\n"
        f"📅 Сегодня      |  {today_payments:>5}\n"
        f"---------------|--------\n"
        f"📊 ДИНАМИКА     |       \n"
        f"  За неделю    |  {week_payments:>5}\n"
        f"  За месяц     |  {month_payments:>5}\n"
        f"```\n\n"
    )

    if popular_tarifs:
        text += "🏆 **Популярные тарифы**\n```\n"
        text += f"Тариф          | Покупки\n"
        text += f"---------------|--------\n"
        for tarif, cnt in popular_tarifs:
            text += f" {tarif:<14}|  {cnt:>5}\n"
        text += "```"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Обновить", callback_data="admin_finance")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")]
    ])

    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()

@stats_router.message(Command("stats"))
async def quick_stats_cmd(message: Message):
    conn = sqlite3.connect("database/data/users.db")
    c = conn.cursor()

    c.execute("SELECT COUNT(*) FROM users")
    total_users = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM subscriptions WHERE status = 'active'")
    active_subs = c.fetchone()[0]

    today = datetime.now().strftime("%Y-%m-%d")
    c.execute("SELECT COUNT(*) FROM users WHERE reg_date LIKE ?", (f"{today}%",))
    today_users = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM payments WHERE status = 'completed'")
    payments = c.fetchone()[0]

    conn.close()

    await message.answer(
        f"📊 **Быстрая статистика**\n\n"
        f"👥 Всего: **{total_users}**\n"
        f"✅ Активных: **{active_subs}**\n"
        f"🆕 Сегодня: **{today_users}**\n"
        f"💳 Платежей: **{payments}**",
        parse_mode="Markdown"
    )
