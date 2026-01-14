import asyncio
import logging
import sqlite3
import requests
from datetime import datetime

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# ================== НАСТРОЙКИ ==================
BOT_TOKEN = "8570392401:AAFfowtqYzjxz-PCC-0IVJPx1xl5V03LCXk"
ADMIN_ID = 8479289622

HIDDIFY_ADMIN_PATH = "https://vpn.tgflovv.ru/a2NRdl78IHwZBYBReUx"
HIDDIFY_CLIENT_PATH = "https://vpn.tgflovv.ru/6bqCF1dLYRFoerALhhXu8cn98"

API_KEY = "245320ca-f07d-401b-9f43-000735d93085"

DEEPLINK_BASE = "https://deeplink.website/link?url_ha="

CHANNEL_USERNAME = "@MAGAMIX_VPN"
CHANNEL_LINK = "https://t.me/MAGAMIX_VPN"

TARIFS = {
    "7 дней": (7, 50),
    "1 месяц": (30, 150),
    "3 месяца": (90, 350),
    "6 месяцев": (180, 600),
    "12 месяцев": (365, 1000)
}

HAPP_LINKS = {
    "Android": "https://play.google.com/store/apps/details?id=com.happproxy&hl=ru&pli=1",
    "iOS": "https://apps.apple.com/ru/app/happ-proxy-utility-plus/id6746188973",
    "Windows": "https://github.com/Happ-proxy/happ-desktop/releases/latest/download/setup-Happ.x64.exe",
    "MacOS": "https://apps.apple.com/ru/app/happ-proxy-utility-plus/id6746188973"
}

# База данных
DB_FILE = "users.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            reg_date TEXT,
            got_free INTEGER DEFAULT 0
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            uuid TEXT UNIQUE,
            days INTEGER,
            created_at TEXT,
            status TEXT DEFAULT 'active'
        )
    ''')
    conn.commit()
    conn.close()

init_db()

def add_user_if_new(user_id: int, username: str):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
    if not c.fetchone():
        reg_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        c.execute("INSERT INTO users (user_id, username, reg_date) VALUES (?, ?, ?)",
                  (user_id, username, reg_date))
        conn.commit()
        conn.close()
        return True  # новый
    conn.close()
    return False

def user_got_free(user_id: int):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT got_free FROM users WHERE user_id = ?", (user_id,))
    result = c.fetchone()
    conn.close()
    return result[0] == 1 if result else False

def mark_got_free(user_id: int):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE users SET got_free = 1 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

# Создание пользователя в Hiddify
def create_hiddify_user(days: int, user_id: int):
    url = f"{HIDDIFY_ADMIN_PATH}/api/v2/admin/user/"
    headers = {"Hiddify-API-Key": API_KEY, "Content-Type": "application/json"}
    payload = {
        "name": "",
        "package_days": days,
        "usage_limit_GB": 0,
        "mode": "no_reset"
    }
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=15)
        response.raise_for_status()
        data = response.json()
        uuid = data.get("uuid")
        if uuid:
            # Сохраняем подписку в БД
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            c.execute("INSERT INTO subscriptions (user_id, uuid, days, created_at, status) VALUES (?, ?, ?, ?, ?)",
                      (user_id, uuid, days, created_at, "active"))
            conn.commit()
            conn.close()

            profile_link = f"{HIDDIFY_CLIENT_PATH}/{uuid}/"
            deeplink = f"{DEEPLINK_BASE}{profile_link}"
            return deeplink
        return None
    except Exception as e:
        logging.error(f"Ошибка API: {e}")
        return None
# Главное меню
async def send_main_menu(event, user_name, user_id):
    text = (
        f"Привет, {user_name} 👋\n\n"
        "Magam VPN — премиум VPN в РФ 🚀\n\n"
        "Избавим тебя от:\n"
        "📉 Зависающих видео\n"
        "🔋 Утекающего заряда батареи на пробных VPN\n\n"
        "Пригласи друзей и получи 3 дня доступа за каждого! 🎁\n"
        "Твои друзья тоже получат 3 дня бесплатно!"
    )
    kb = [
        [InlineKeyboardButton(text="💳 Оплатить VPN", callback_data="pay")],
        [InlineKeyboardButton(text="📲 Установить VPN", callback_data="install")],
        [InlineKeyboardButton(text="👥 Пригласить друзей", callback_data="referral")],
        [InlineKeyboardButton(text="🆘 Поддержка", url="t.me/magamix_support")]
    ]
    if not user_got_free(user_id):
        kb.insert(1, [InlineKeyboardButton(text="🎁 Бесплатно 3 дня", callback_data="free_3days")])

    markup = InlineKeyboardMarkup(inline_keyboard=kb)

    if isinstance(event, Message):
        await event.answer(text, reply_markup=markup)
    else:
        await event.message.edit_text(text, reply_markup=markup)

def get_user_subscriptions(user_id: int):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT uuid, days, created_at FROM subscriptions WHERE user_id = ? AND status = 'active'", (user_id,))
    subs = c.fetchall()
    conn.close()
    return subs

# Старт
@dp.message(Command("start"))
async def start(message: Message):
    name = message.from_user.first_name
    user_id = message.from_user.id
    username = message.from_user.username or "нет"

    is_new = add_user_if_new(user_id, username)
    if is_new:
        await bot.send_message(ADMIN_ID, f"Новый пользователь: {message.from_user.full_name} (ID: {user_id})")

    await send_main_menu(message, name, user_id)

# Оплата
@dp.callback_query(F.data == "pay")
async def pay(callback: CallbackQuery):
    await callback.message.edit_text("💸 Выбери тариф:", reply_markup=tarifs_menu())

def tarifs_menu():
    kb = []
    for name, (days, price) in TARIFS.items():
        text = f"{name} — {price}₽"
        if days > 30:
            monthly = round(price / (days / 30))
            text += f" ({monthly}₽/мес)"
        kb.append([InlineKeyboardButton(text=text, callback_data=f"tarif_{name}")])
    kb.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

@dp.callback_query(F.data.startswith("tarif_"))
async def tarif_chosen(callback: CallbackQuery, state: FSMContext):
    tarif_name = callback.data.split("_", 1)[1]
    days, price = TARIFS[tarif_name]
    await state.update_data(tarif=tarif_name, days=days, price=price)

    text = (
        f"Последний штрих ⚡\n\n"
        f"Оплата:\nНомер: 79283376737\nБанк: ОЗОН БАНК\nСумма: {price}₽\n\n"
        f"Нажми «Я оплатил» и пришли скрин."
    )
    kb = [
        [InlineKeyboardButton(text="✅ Я оплатил", callback_data="paid")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="pay")]
    ]
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    await state.set_state(States.waiting_payment_screenshot)

@dp.callback_query(F.data == "paid", States.waiting_payment_screenshot)
async def waiting_screenshot(callback: CallbackQuery):
    await callback.message.edit_text("📸 Отправь скриншот перевода. Админ проверит.")
    # Состояние остаётся для фото

@dp.message((F.photo | F.document), States.waiting_payment_screenshot)
async def get_screenshot(message: Message, state: FSMContext):
    data = await state.get_data()
    user = message.from_user
    text = (
        f"🔥 НОВАЯ ОПЛАТА!\n"
        f"Пользователь: {user.full_name} (@{user.username or 'нет'})\n"
        f"ID: {user.id}\n"
        f"Тариф: {data['tarif']} ({data['days']} дней, {data['price']}₽)"
    )
    kb = [
        [InlineKeyboardButton(text="✅ Выдать", callback_data=f"approve_{user.id}_{data['days']}")],
        [InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_{user.id}")]
    ]
    if message.photo:
        await bot.send_photo(ADMIN_ID, message.photo[-1].file_id, caption=text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    else:
        await bot.send_document(ADMIN_ID, message.document.file_id, caption=text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    await message.answer("✅ Чек отправлен админу!", reply_markup=main_menu())
    await state.clear()

@dp.callback_query(F.data.startswith("approve_"))
async def approve(callback: CallbackQuery):
    _, user_id_str, days_str = callback.data.split("_")
    user_id = int(user_id_str)
    days = int(days_str)

    deeplink = create_hiddify_user(days)
    if deeplink:
        await bot.send_message(user_id, f"🎉 Оплата подтверждена!\n\nТвоя подписка на {days} дней:\n{deeplink}")
        await callback.answer("Выдано!")
    else:
        await bot.send_message(ADMIN_ID, f"❌ Ошибка создания подписки для {user_id}")
        await callback.answer("Ошибка")

@dp.callback_query(F.data.startswith("reject_"))
async def reject(callback: CallbackQuery):
    _, user_id = callback.data.split("_")
    await bot.send_message(int(user_id), "❌ Оплата не подтверждена. Проверь данные или пиши в поддержку.")
    await callback.answer("Отклонено")

# Бесплатные 3 дня
@dp.callback_query(F.data == "free_3days")
async def free_3days(callback: CallbackQuery, state: FSMContext):
    text = f"Хочешь 3 дня бесплатно? 🎁\n\nПодпишись на канал {CHANNEL_USERNAME}"
    kb = [
        [InlineKeyboardButton(text="📢 Подписаться", url=CHANNEL_LINK)],
        [InlineKeyboardButton(text="✅ Проверить", callback_data="check_free_sub")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")]
    ]
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    await state.set_state(States.waiting_free_check)

@dp.callback_query(F.data == "check_free_sub", States.waiting_free_check)
async def check_free_sub(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    try:
        member = await bot.get_chat_member(CHANNEL_USERNAME, user_id)
        if member.status in ("member", "administrator", "creator"):
            if user_got_free(user_id):
                await callback.message.edit_text("У тебя уже есть бесплатные 3 дня! Перейди в «Установить VPN»")
            else:
                deeplink = create_hiddify_user(3)
                if deeplink:
                    await callback.message.edit_text(
                        "🎉 Подписка подтверждена!\n\n"
                        "Подписка на 3 дня выдана!\n\n"
                        "Подключиться можете через главное меню → «Установить VPN»"
                    )
                    mark_got_free(user_id)
                    await bot.send_message(ADMIN_ID, f"Бесплатно 3 дня выданы: {callback.from_user.full_name} ({user_id})")
                else:
                    await callback.message.edit_text("❌ Ошибка выдачи. Напиши в поддержку.")
        else:
            await callback.answer("Не подписан! Подпишись и попробуй снова.", show_alert=True)
    except Exception:
        await callback.answer("Ошибка проверки. Бот должен быть админом канала.", show_alert=True)
    await state.clear()

# Установить VPN
@dp.callback_query(F.data == "install")
async def install(callback: CallbackQuery):
    user_id = callback.from_user.id
    subs = get_user_subscriptions(user_id)

    if subs:
        text = "Твои активные подписки:\n\n"
        kb = []
        for uuid, days, created in subs:
            text += f"• {days} дней (создана {created})\n"
            deeplink = f"{DEEPLINK_BASE}{HIDDIFY_CLIENT_PATH}/{uuid}/"
            kb.append([InlineKeyboardButton(text=f"Подключить ({days} дней)", url=deeplink)])
        kb.append([InlineKeyboardButton(text="🔙 Главное меню", callback_data="back_main")])
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    else:
        text = "У тебя нет активных подписок.\n\nОформи тариф или возьми 3 дня бесплатно!"
        kb = [
            [InlineKeyboardButton(text="💳 Оплатить VPN", callback_data="pay")],
            [InlineKeyboardButton(text="🎁 Бесплатно 3 дня", callback_data="free_3days")],
            [InlineKeyboardButton(text="🔙 Главное меню", callback_data="back_main")]
        ]
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
        
# Пригласить друзей
@dp.callback_query(F.data == "referral")
async def referral(callback: CallbackQuery):
    name = callback.from_user.first_name
    bot_username = (await bot.get_me()).username
    ref_link = f"https://t.me/{bot_username}?start=ref_{callback.from_user.id}"
    text = (
        f"{name}, за каждого друга — 3 дня VPN тебе и ему! 🎁\n\n"
        f"Твоя реферальная ссылка:"
    )
    kb = [
        [InlineKeyboardButton(text="📤 Поделиться", url=f"https://t.me/share/url?url={ref_link}")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")]
    ]
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@dp.callback_query(F.data == "back_main")
async def back_main(callback: CallbackQuery):
    await send_main_menu(callback, callback.from_user.first_name, callback.from_user.id)

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
