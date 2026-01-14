import asyncio
import logging
import sqlite3
import requests

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
    conn.commit()
    conn.close()

init_db()

# ================================================

bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
logging.basicConfig(level=logging.INFO)

class States(StatesGroup):
    waiting_payment_screenshot = State()
    waiting_free_check = State()

# Получить статус бесплатных дней
def user_got_free(user_id: int):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT got_free FROM users WHERE user_id = ?", (user_id,))
    result = c.fetchone()
    conn.close()
    return result[0] == 1 if result else False

# Отметить получение бесплатных дней
def mark_got_free(user_id: int):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO users (user_id, got_free) VALUES (?, 1)", (user_id,))
    conn.commit()
    conn.close()

# Создание пользователя в Hiddify (имя пустое, ссылка в нужном формате)
def create_hiddify_user(days: int):
    url = f"{HIDDIFY_ADMIN_PATH}/api/v2/admin/user/"
    headers = {"Hiddify-API-Key": API_KEY, "Content-Type": "application/json"}
    payload = {
        "name": "",  # Пустое имя
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
            profile_link = f"{HIDDIFY_CLIENT_PATH}/{uuid}/"
            deeplink = f"{DEEPLINK_BASE}{profile_link}"
            return deeplink
        return None
    except Exception as e:
        logging.error(f"Ошибка API: {e}")
        return None

# Главное меню (кнопка бесплатных дней только если не получал)
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

# Старт
@dp.message(Command("start"))
async def start(message: Message):
    name = message.from_user.first_name
    user_id = message.from_user.id
    await send_main_menu(message, name, user_id)
    await bot.send_message(ADMIN_ID, f"Новый пользователь: {message.from_user.full_name} (ID: {user_id})")

# Оплата (оставляем как было, добавь свои хендлеры если нужно)
@dp.callback_query(F.data == "pay")
async def pay(callback: CallbackQuery):
    await callback.message.edit_text("💸 Выбери тариф:", reply_markup=tarifs_menu())

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
                    mark_got_free(user_id)  # ставим флаг
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
    text = "У тебя нет активных подписок.\nОформи тариф или возьми 3 дня бесплатно!"
    kb = [
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
