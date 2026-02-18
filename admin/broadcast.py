import sqlite3
import asyncio
from aiogram import F, Router
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config.settings import ADMIN_IDS

broadcast_router = Router()

broadcast_router.message.filter(lambda message: message.from_user.id in ADMIN_IDS)
broadcast_router.callback_query.filter(lambda callback: callback.from_user.id in ADMIN_IDS)

class BroadcastStates(StatesGroup):
    waiting_broadcast = State()
    waiting_confirm = State()

@broadcast_router.callback_query(F.data == "admin_broadcast")
async def admin_broadcast(callback: CallbackQuery, state: FSMContext):
    conn = sqlite3.connect("database/data/users.db")
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users")
    total = c.fetchone()[0]
    conn.close()

    text = (
        "📤 **РАССЫЛКА**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👥 Получателей: **{total}**\n\n"
        "Введите текст для рассылки.\n"
        "Поддерживается **Markdown** форматирование."
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")]
    ])

    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    await state.set_state(BroadcastStates.waiting_broadcast)
    await callback.answer()

@broadcast_router.message(BroadcastStates.waiting_broadcast)
async def process_broadcast(message: Message, state: FSMContext):
    broadcast_text = message.text

    conn = sqlite3.connect("database/data/users.db")
    c = conn.cursor()
    c.execute("SELECT user_id FROM users")
    user_ids = [row[0] for row in c.fetchall()]
    conn.close()

    await state.update_data(broadcast_text=broadcast_text, user_ids=user_ids)

    preview = broadcast_text[:200] + ("..." if len(broadcast_text) > 200 else "")

    text = (
        f"📤 **ПОДТВЕРЖДЕНИЕ РАССЫЛКИ**\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👥 Получателей: **{len(user_ids)}**\n\n"
        f"📝 **Превью:**\n{preview}\n\n"
        f"Отправить?"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Отправить", callback_data="broadcast_confirm"),
            InlineKeyboardButton(text="❌ Отмена", callback_data="broadcast_cancel")
        ]
    ])

    await message.answer(text, reply_markup=kb, parse_mode="Markdown")
    await state.set_state(BroadcastStates.waiting_confirm)

@broadcast_router.callback_query(F.data == "broadcast_confirm")
async def broadcast_confirm(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    broadcast_text = data.get("broadcast_text", "")
    user_ids = data.get("user_ids", [])

    if not broadcast_text or not user_ids:
        await callback.answer("❌ Ошибка: нет данных для рассылки")
        await state.clear()
        return

    progress_msg = await callback.message.edit_text(
        "📤 **Рассылка началась...**\n\n⏳ 0%",
        parse_mode="Markdown"
    )

    sent = 0
    failed = 0
    total = len(user_ids)

    for i, user_id in enumerate(user_ids):
        try:
            await callback.bot.send_message(user_id, broadcast_text, parse_mode="Markdown")
            sent += 1
        except:
            failed += 1

        if (i + 1) % 30 == 0 or i == total - 1:
            percent = int(((i + 1) / total) * 100)
            bar_filled = int(percent / 10)
            bar = "▓" * bar_filled + "░" * (10 - bar_filled)
            try:
                await progress_msg.edit_text(
                    f"📤 **Рассылка...**\n\n"
                    f"{bar} {percent}%\n\n"
                    f"✅ {sent} | ❌ {failed} | 📊 {i+1}/{total}",
                    parse_mode="Markdown"
                )
            except:
                pass

        await asyncio.sleep(0.05)

    await progress_msg.edit_text(
        f"📤 **РАССЫЛКА ЗАВЕРШЕНА**\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"✅ Доставлено: **{sent}**\n"
        f"❌ Не доставлено: **{failed}**\n"
        f"📊 Успешность: **{(sent / max(total, 1)) * 100:.1f}%**",
        parse_mode="Markdown"
    )

    await state.clear()
    await callback.answer()

@broadcast_router.callback_query(F.data == "broadcast_cancel")
async def broadcast_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        "❌ **Рассылка отменена**",
        parse_mode="Markdown"
    )
    await callback.answer()
