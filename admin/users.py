import sqlite3
from datetime import datetime
from aiogram import F, Router
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config.settings import ADMIN_IDS
from services.hiddify_service import HiddifyService

users_router = Router()
hiddify_service = HiddifyService()

users_router.message.filter(lambda message: message.from_user.id in ADMIN_IDS)
users_router.callback_query.filter(lambda callback: callback.from_user.id in ADMIN_IDS)

class UserStates(StatesGroup):
    waiting_user_id = State()
    waiting_days_to_add = State()
    waiting_user_search = State()
    waiting_ban_user_id = State()

@users_router.callback_query(F.data == "admin_users")
async def admin_users(callback: CallbackQuery):
    conn = sqlite3.connect("database/data/users.db")
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users")
    total = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM subscriptions WHERE status = 'active'")
    active = c.fetchone()[0]
    conn.close()

    text = (
        "👥 **ПОЛЬЗОВАТЕЛИ**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📊 Всего: **{total}** | Активных: **{active}**\n\n"
        "Выберите действие:"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔎 Найти пользователя", callback_data="admin_find_user")],
        [InlineKeyboardButton(text="➕ Добавить дни", callback_data="admin_add_days")],
        [InlineKeyboardButton(text="💰 Топ покупателей", callback_data="admin_top_users")],
        [InlineKeyboardButton(text="🚫 Удалить подписку", callback_data="admin_ban_user")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")]
    ])

    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()

@users_router.callback_query(F.data == "admin_find_user")
async def admin_find_user(callback: CallbackQuery, state: FSMContext):
    text = (
        "🔍 **ПОИСК ПОЛЬЗОВАТЕЛЯ**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Введите одно из:\n"
        "┣ **ID** пользователя (число)\n"
        "┗ **Username** (с @ или без)"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_users")]
    ])

    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    await state.set_state(UserStates.waiting_user_search)
    await callback.answer()

def search_user_flexible(query: str):
    query = query.strip().lstrip("@")
    conn = sqlite3.connect("database/data/users.db")
    c = conn.cursor()

    if query.isdigit():
        c.execute("SELECT * FROM users WHERE user_id = ?", (int(query),))
    else:
        c.execute("SELECT * FROM users WHERE LOWER(username) LIKE LOWER(?)", (f"%{query}%",))

    results = c.fetchall()
    conn.close()
    return results

async def build_user_card(user_data, bot=None):
    user_id, username, reg_date, got_free = user_data

    conn = sqlite3.connect("database/data/users.db")
    c = conn.cursor()

    c.execute("SELECT uuid, created_at FROM subscriptions WHERE user_id = ? AND status = 'active'", (user_id,))
    subs = c.fetchall()

    c.execute("SELECT COUNT(*) FROM payments WHERE user_id = ? AND status = 'completed'", (user_id,))
    completed_payments = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM payments WHERE user_id = ? AND status = 'pending'", (user_id,))
    pending_payments = c.fetchone()[0]

    c.execute("SELECT tarif, days, created_at FROM payments WHERE user_id = ? AND status = 'completed' ORDER BY created_at DESC LIMIT 1", (user_id,))
    last_payment = c.fetchone()

    conn.close()

    username_display = f"@{username}" if username and username != "нет" else "не указан"

    tg_name = "—"
    if bot:
        try:
            chat = await bot.get_chat(user_id)
            first = chat.first_name or ""
            last = chat.last_name or ""
            tg_name = f"{first} {last}".strip() or "—"
        except:
            pass

    reg_display = reg_date[:16] if reg_date else "—"

    if reg_date:
        try:
            reg_dt = datetime.strptime(reg_date[:19], "%Y-%m-%d %H:%M:%S")
            days_since = (datetime.now() - reg_dt).days
            reg_display += f" ({days_since}д назад)"
        except:
            pass

    text = (
        f"👤 **КАРТОЧКА ПОЛЬЗОВАТЕЛЯ**\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🆔 **ID:** `{user_id}`\n"
        f"📛 **Имя:** {tg_name}\n"
        f"👤 **Username:** {username_display}\n"
        f"📅 **Регистрация:** {reg_display}\n"
        f"🎁 **Пробный период:** {'✅ Использован' if got_free else '❌ Не брал'}\n\n"
    )

    text += f"💳 **ПЛАТЕЖИ**\n"
    text += f"┣ Успешных: **{completed_payments}**\n"
    text += f"┗ Ожидающих: **{pending_payments}**\n"
    if last_payment:
        tarif, days, pay_date = last_payment
        text += f"     📌 Последний: {tarif} ({days}д) — {pay_date[:16]}\n"
    text += "\n"

    text += f"📡 **ПОДПИСКИ** ({len(subs)})\n"
    if subs:
        for i, (uuid, created_at) in enumerate(subs):
            remaining = hiddify_service.get_remaining_days(uuid)
            if remaining > 7:
                status_icon = "🟢"
            elif remaining > 0:
                status_icon = "🟡"
            else:
                status_icon = "🔴"
            text += f"┣ {status_icon} `{uuid[:12]}...`\n"
            text += f"┃   ⏳ Осталось: **{remaining}** дн.\n"
    else:
        text += "┗ Нет активных подписок\n"

    return text

@users_router.message(UserStates.waiting_user_search)
async def process_user_search(message: Message, state: FSMContext):
    query = message.text.strip()
    results = search_user_flexible(query)

    if not results:
        await message.answer(
            f"❌ **Пользователь не найден**\n\n"
            f"Запрос: `{query}`\n"
            f"Попробуйте другой ID или username.",
            parse_mode="Markdown"
        )
        await state.clear()
        return

    if len(results) == 1:
        user_data = results[0]
        user_id = user_data[0]
        text = await build_user_card(user_data, bot=message.bot)

        kb = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="➕ Добавить дни", callback_data=f"add_days_{user_id}"),
                InlineKeyboardButton(text="🚫 Удалить подписку", callback_data=f"ban_user_{user_id}")
            ],
            [InlineKeyboardButton(text="🔄 Обновить", callback_data=f"refresh_user_{user_id}")],
            [InlineKeyboardButton(text="🔎 Новый поиск", callback_data="admin_find_user")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_users")]
        ])

        await message.answer(text, reply_markup=kb, parse_mode="Markdown")
    else:
        text = f"🔍 **Найдено {len(results)} пользователей:**\n━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        buttons = []
        for user_data in results[:10]:
            uid, uname, reg, _ = user_data
            uname_display = f"@{uname}" if uname and uname != "нет" else f"ID:{uid}"
            text += f"• {uname_display} — `{uid}`\n"
            buttons.append([InlineKeyboardButton(text=f"👤 {uname_display}", callback_data=f"refresh_user_{uid}")])

        if len(results) > 10:
            text += f"\n... и ещё {len(results) - 10}"

        buttons.append([InlineKeyboardButton(text="🔎 Новый поиск", callback_data="admin_find_user")])
        buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="admin_users")])

        await message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="Markdown")

    await state.clear()

@users_router.callback_query(F.data.startswith("refresh_user_"))
async def refresh_user(callback: CallbackQuery):
    user_id = int(callback.data.replace("refresh_user_", ""))

    conn = sqlite3.connect("database/data/users.db")
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user_data = c.fetchone()
    conn.close()

    if not user_data:
        await callback.answer("❌ Пользователь не найден")
        return

    text = await build_user_card(user_data, bot=callback.bot)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="➕ Добавить дни", callback_data=f"add_days_{user_id}"),
            InlineKeyboardButton(text="🚫 Удалить подписку", callback_data=f"ban_user_{user_id}")
        ],
        [InlineKeyboardButton(text="🔄 Обновить", callback_data=f"refresh_user_{user_id}")],
        [InlineKeyboardButton(text="🔎 Новый поиск", callback_data="admin_find_user")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_users")]
    ])

    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()

@users_router.callback_query(F.data == "admin_add_days")
async def admin_add_days(callback: CallbackQuery, state: FSMContext):
    text = (
        "➕ **ДОБАВИТЬ ДНИ**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Введите ID пользователя:"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_users")]
    ])

    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    await state.set_state(UserStates.waiting_user_id)
    await callback.answer()

@users_router.callback_query(F.data.startswith("add_days_"))
async def add_days_to_user(callback: CallbackQuery, state: FSMContext):
    user_id = int(callback.data.replace("add_days_", ""))
    await state.update_data(target_user_id=user_id)

    text = (
        f"➕ **ДОБАВИТЬ ДНИ**\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👤 Пользователь: `{user_id}`\n\n"
        f"Введите количество дней:"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_users")]
    ])

    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    await state.set_state(UserStates.waiting_days_to_add)
    await callback.answer()

@users_router.message(UserStates.waiting_user_id)
async def process_user_id(message: Message, state: FSMContext):
    try:
        user_id = int(message.text.strip())
        await state.update_data(target_user_id=user_id)

        await message.answer(
            f"👤 Пользователь: `{user_id}`\n\n"
            "Введите количество дней для добавления:",
            parse_mode="Markdown"
        )
        await state.set_state(UserStates.waiting_days_to_add)

    except ValueError:
        await message.answer("❌ Неверный формат. Введите числовой ID.")

@users_router.message(UserStates.waiting_days_to_add)
async def process_days_to_add(message: Message, state: FSMContext):
    try:
        days = int(message.text.strip())
        if days <= 0 or days > 365:
            await message.answer("❌ Введите число от 1 до 365.")
            return

        data = await state.get_data()
        target_user_id = data["target_user_id"]

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
            text = (
                f"✅ **ДНЕЙ ДОБАВЛЕНО**\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"👤 Пользователь: `{target_user_id}`\n"
                f"📦 Добавлено: **+{days} дней**\n"
                f"🕐 Время: {datetime.now().strftime('%H:%M:%S')}"
            )

            try:
                await message.bot.send_message(
                    target_user_id,
                    f"🎁 **Подарок от администрации!**\n\n"
                    f"Вам добавлено **{days} дней** VPN!\n"
                    f"Спасибо что вы с нами! 💙",
                    parse_mode="Markdown"
                )
                text += "\n\n📨 Пользователь уведомлён"
            except:
                text += "\n\n⚠️ Не удалось уведомить пользователя"

            await message.answer(text, parse_mode="Markdown")
        else:
            await message.answer("❌ Ошибка при добавлении дней. Проверьте ID пользователя.")

        await state.clear()

    except ValueError:
        await message.answer("❌ Введите число от 1 до 365.")

@users_router.callback_query(F.data == "admin_top_users")
async def admin_top_users(callback: CallbackQuery):
    conn = sqlite3.connect("database/data/users.db")
    c = conn.cursor()

    c.execute("""
        SELECT u.user_id, u.username, COUNT(p.id) as payment_count, SUM(p.days) as total_days
        FROM users u 
        LEFT JOIN payments p ON u.user_id = p.user_id AND p.status = 'completed'
        GROUP BY u.user_id, u.username
        HAVING payment_count > 0
        ORDER BY payment_count DESC, total_days DESC
        LIMIT 10
    """)
    top_users = c.fetchall()
    conn.close()

    text = "🏆 **ТОП ПОКУПАТЕЛЕЙ**\n━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"

    if not top_users:
        text += "Пока нет покупателей."
    else:
        medals = ["🥇", "🥈", "🥉"]
        for i, (user_id, username, payment_count, total_days) in enumerate(top_users):
            medal = medals[i] if i < 3 else f"  {i+1}."
            username_display = f"@{username}" if username and username != "нет" else f"`{user_id}`"
            total_days = total_days or 0
            text += f"{medal} {username_display}\n     💳 {payment_count} платежей • {total_days} дней\n"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Обновить", callback_data="admin_top_users")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_users")]
    ])

    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()

@users_router.callback_query(F.data == "admin_ban_user")
async def admin_ban_user(callback: CallbackQuery, state: FSMContext):
    text = (
        "🚫 **УДАЛЕНИЕ ПОДПИСКИ**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Введите ID пользователя, которому нужно\n"
        "удалить подписку с серверов:"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_users")]
    ])

    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    await state.set_state(UserStates.waiting_ban_user_id)
    await callback.answer()

@users_router.callback_query(F.data.startswith("ban_user_"))
async def ban_user_direct(callback: CallbackQuery):
    user_id = int(callback.data.replace("ban_user_", ""))
    await _do_ban_user(user_id, callback.message, callback.bot)
    await callback.answer()

@users_router.message(UserStates.waiting_ban_user_id)
async def process_ban_user_id(message: Message, state: FSMContext):
    try:
        user_id = int(message.text.strip())
        await _do_ban_user(user_id, message, message.bot)
    except ValueError:
        await message.answer("❌ Неверный формат. Введите числовой ID.")
    await state.clear()

async def _do_ban_user(user_id: int, msg_target, bot):
    from database.models import get_user_subscriptions, update_subscription_status

    subs = get_user_subscriptions(user_id)

    if not subs:
        await msg_target.answer(
            f"❌ У пользователя `{user_id}` нет активных подписок.",
            parse_mode="Markdown"
        )
        return

    deleted_count = 0
    for uuid, _ in subs:
        hiddify_service.delete_user(uuid, "RU")
        hiddify_service.delete_user(uuid, "NL")
        update_subscription_status(uuid, "revoked")
        deleted_count += 1

    text = (
        f"🚫 **ПОДПИСКИ УДАЛЕНЫ**\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👤 Пользователь: `{user_id}`\n"
        f"🗑 Удалено подписок: **{deleted_count}**\n"
        f"🕐 {datetime.now().strftime('%H:%M:%S')}"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 К пользователям", callback_data="admin_users")]
    ])

    await msg_target.answer(text, reply_markup=kb, parse_mode="Markdown")

@users_router.callback_query(F.data.startswith("admin_add_days_"))
async def admin_add_days_legacy(callback: CallbackQuery, state: FSMContext):
    user_id = int(callback.data.split("_")[-1])
    await state.update_data(target_user_id=user_id)

    text = f"➕ Добавить дни пользователю `{user_id}`\n\nВведите количество дней:"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_users")]
    ])

    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    await state.set_state(UserStates.waiting_days_to_add)
    await callback.answer()

@users_router.callback_query(F.data.startswith("admin_user_details_"))
async def admin_user_details(callback: CallbackQuery):
    user_id = int(callback.data.split("_")[-1])

    conn = sqlite3.connect("database/data/users.db")
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user_data = c.fetchone()
    conn.close()

    if not user_data:
        await callback.answer("❌ Пользователь не найден")
        return

    text = await build_user_card(user_data, bot=callback.bot)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="➕ Добавить дни", callback_data=f"add_days_{user_id}"),
            InlineKeyboardButton(text="🚫 Удалить подписку", callback_data=f"ban_user_{user_id}")
        ],
        [InlineKeyboardButton(text="🔄 Обновить", callback_data=f"refresh_user_{user_id}")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_users")]
    ])

    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()
