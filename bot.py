import asyncio
import logging
from datetime import datetime, timedelta
import random
import string
import requests

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# ================== НАСТРОЙКИ ==================
BOT_TOKEN = "8570392401:AAFfowtqYzjxz-PCC-0IVJPx1xl5V03LCXk"  # ← Замени на свой токен

ADMIN_ID = 8479289622  # ← Замени на свой Telegram ID (узнай у @userinfobot)

# Hiddify настройки — твои реальные значения
HIDDIFY_ADMIN_PATH = "https://vpn.tgflovv.ru/a2NRdl78IHwZBYBReUx"
HIDDIFY_CLIENT_PATH = "https://vpn.tgflovv.ru/6bqCF1dLYRFoerALhhXu8cn98"
API_KEY = "245320ca-f07d-401b-9f43-000735d93085"  # твой рабочий ключ

DEEPLINK_BASE = "https://deeplink.website/link?url_ha="

# Тарифы (название: (дни, цена в рублях))
TARIFS = {
    "7 дней": (7, 50),
    "1 месяц": (30, 150),
    "3 месяца": (90, 350),
    "6 месяцев": (180, 600),
    "12 месяцев": (365, 1000)
}

# Ссылки на Happ Proxy
HAPP_LINKS = {
    "Android": "https://play.google.com/store/apps/details?id=com.happproxy&hl=ru&pli=1",
    "iOS": "https://apps.apple.com/ru/app/happ-proxy-utility-plus/id6746188973",
    "Windows": "https://github.com/Happ-proxy/happ-desktop/releases/latest/download/setup-Happ.x64.exe",
    "MacOS": "https://apps.apple.com/ru/app/happ-proxy-utility-plus/id6746188973"
}

# ================================================

bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
logging.basicConfig(level=logging.INFO)

class States(StatesGroup):
    waiting_payment_screenshot = State()

# Главное меню
def main_menu():
    kb = [
        [InlineKeyboardButton(text="💳 Оплатить VPN", callback_data="pay")],
        [InlineKeyboardButton(text="📲 Установить VPN", callback_data="install")],
        [InlineKeyboardButton(text="👥 Пригласить друзей", callback_data="referral")],
        [InlineKeyboardButton(text="🆘 Поддержка", url="t.me/magamix_support")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

# Меню тарифов
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

# Устройства для установки
def devices_menu():
    kb = [
        [InlineKeyboardButton(text="🤖 Android", callback_data="device_Android")],
        [InlineKeyboardButton(text="🍎 iOS", callback_data="device_iOS")],
        [InlineKeyboardButton(text="💻 Windows", callback_data="device_Windows")],
        [InlineKeyboardButton(text="🖥 MacOS", callback_data="device_MacOS")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

# Функция создания пользователя в Hiddify
def create_hiddify_user(days: int, user_name: str = "BotUser"):
    url = f"{HIDDIFY_ADMIN_PATH}/api/v2/admin/user/"
    headers = {
        "Hiddify-API-Key": API_KEY,
        "Content-Type": "application/json"
    }
    payload = {
        "name": user_name,
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
            sub_link = f"{HIDDIFY_CLIENT_PATH}/sub/{uuid}"
            deeplink = f"{DEEPLINK_BASE}{sub_link}"
            return deeplink
        else:
            logging.error(f"Нет uuid в ответе: {data}")
            return None
    except Exception as e:
        logging.error(f"Ошибка API: {str(e)} | Ответ: {response.text if 'response' in locals() else ''}")
        return None

# Старт
@dp.message(Command("start"))
async def start(message: Message):
    name = message.from_user.first_name
    text = (
        f"Привет, {name} 👋\n\n"
        "Magam VPN — премиум VPN в РФ 🚀\n\n"
        "Избавим тебя от:\n"
        "📉 Зависающих видео\n"
        "🔋 Утекающего заряда батареи на пробных VPN\n\n"
        "Пригласи друзей и получи 3 дня доступа за каждого! 🎁\n"
        "Твои друзья тоже получат 3 дня бесплатно!"
    )
    await message.answer(text, reply_markup=main_menu())

# Оплата
@dp.callback_query(F.data == "pay")
async def pay(callback: CallbackQuery):
    await callback.message.edit_text("💸 Выбери тариф:", reply_markup=tarifs_menu())

@dp.callback_query(F.data.startswith("tarif_"))
async def tarif_chosen(callback: CallbackQuery, state: FSMContext):
    tarif_name = callback.data.split("_", 1)[1]
    days, price = TARIFS[tarif_name]
    await state.update_data(tarif=tarif_name, days=days, price=price)

    text = (
        f"Последний штрих, и ты почувствуешь ⚡ скорость и стабильность!\n\n"
        f"1) Оплата:\n"
        f"Номер телефона: 79283376737\n"
        f"Банк: ОЗОН БАНК\n"
        f"Сумма: {price}₽\n\n"
        f"2) Нажми «Я оплатил» и отправь скриншот перевода для проверки."
    )
    kb = [
        [InlineKeyboardButton(text="✅ Я оплатил", callback_data="paid")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="pay")]
    ]
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    await state.set_state(States.waiting_payment_screenshot)

@dp.callback_query(F.data == "paid", States.waiting_payment_screenshot)
async def waiting_screenshot(callback: CallbackQuery):
    await callback.message.edit_text("📸 Отправь скриншот или файл чека перевода. Админ проверит и выдаст подписку.")
    # Состояние остаётся для получения фото/документа

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
    await message.answer("✅ Чек отправлен админу. Ожидай проверки (обычно 5–15 мин).", reply_markup=main_menu())
    await state.clear()

# Админ подтверждает оплату → бот создаёт юзера автоматически
@dp.callback_query(F.data.startswith("approve_"))
async def approve(callback: CallbackQuery):
    _, user_id_str, days_str = callback.data.split("_")
    user_id = int(user_id_str)
    days = int(days_str)

    deeplink = create_hiddify_user(days, f"User_{user_id}_{days}d")
    if deeplink:
        await bot.send_message(user_id, f"🎉 Оплата подтверждена!\n\nТвоя подписка на {days} дней:\n{deeplink}\n\nУстанови Happ и добавь подписку!\n\nЕсли проблемы — пиши в поддержку.")
        await callback.answer("Выдано автоматически!")
    else:
        await bot.send_message(ADMIN_ID, f"❌ Ошибка создания подписки для {user_id}! Проверь логи бота.")
        await callback.answer("Ошибка")

@dp.callback_query(F.data.startswith("reject_"))
async def reject(callback: CallbackQuery):
    _, user_id = callback.data.split("_")
    await bot.send_message(int(user_id), "❌ Оплата не подтверждена. Проверь данные или напиши в поддержку.")
    await callback.answer("Отклонено")

# Установка VPN
@dp.callback_query(F.data == "install")
async def install(callback: CallbackQuery):
    await callback.message.edit_text("📱 Выбери своё устройство для получения инструкции:", reply_markup=devices_menu())

@dp.callback_query(F.data.startswith("device_"))
async def device_chosen(callback: CallbackQuery):
    device = callback.data.split("_")[1]
    link = HAPP_LINKS[device]
    text = (
        "Скачай и установи приложение Happ Proxy:\n\n"
        "1. Нажми «Скачать приложение»\n"
        "2. Вставь свою подписку нажатием «Добавить подписку»\n"
        "3. Нажми большую кнопку в приложении и наслаждайся скоростью! ⚡"
    )
    kb = [
        [InlineKeyboardButton(text="📥 Скачать приложение", url=link)],
        [InlineKeyboardButton(text="🔗 Добавить подписку", callback_data="add_sub_placeholder")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="install")]
    ]
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb), disable_web_page_preview=True)

# Пригласить друзей
@dp.callback_query(F.data == "referral")
async def referral(callback: CallbackQuery):
    name = callback.from_user.first_name
    bot_username = (await bot.get_me()).username
    ref_link = f"https://t.me/{bot_username}?start=ref_{callback.from_user.id}"
    text = (
        f"{name}, ты знал(а), что за каждого приглашённого друга ты получишь 3 дня VPN в подарок? 🎁\n\n"
        f"Вот твоя реферальная ссылка:"
    )
    kb = [
        [InlineKeyboardButton(text="📤 Поделиться ссылкой", url=f"https://t.me/share/url?url={ref_link}")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")]
    ]
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@dp.callback_query(F.data == "back_main")
async def back_main(callback: CallbackQuery):
    await callback.message.edit_text("Главное меню:", reply_markup=main_menu())

# Заглушка для будущей кнопки "Добавить подписку"
@dp.callback_query(F.data == "add_sub_placeholder")
async def add_sub_placeholder(callback: CallbackQuery):
    await callback.answer("Эта функция пока в разработке. Просто скопируй ссылку подписки и вставь в Happ вручную!", show_alert=True)

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
