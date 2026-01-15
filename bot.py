import asyncio
import logging
import sqlite3
import requests
from datetime import datetime

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message, LabeledPrice, PreCheckoutQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from yookassa import Configuration, Payment
from yookassa.domain.notification import WebhookNotification
from uuid import uuid4
from aiohttp import web


# ================== НАСТРОЙКИ ==================
BOT_TOKEN = "8255308077:AAEenB9nueeR37FQy5zhg0W3gryElnJjcYk"
ADMIN_ID = 8479289622
YOOKASSA_SHOP_ID = "1247494"
YOOKASSA_SECRET_KEY = "live_TgYfc-8htgDHnwfEyTSsQSoZcAgcKDTshD8gMXZSpFU"
Configuration.account_id = YOOKASSA_SHOP_ID
Configuration.secret_key = YOOKASSA_SECRET_KEY

HIDDIFY_ADMIN_PATH = "https://vpn.tgflovv.ru/a2NRdl78IHwZBYBReUx"
HIDDIFY_CLIENT_PATH = "https://vpn.tgflovv.ru/6bqCF1dLYRFoerALhhXu8cn98"

API_KEY = "245320ca-f07d-401b-9f43-000735d93085"

DEEPLINK_BASE = "https://deeplink.website/link?url_ha="

CHANNEL_USERNAME = "@MAGAMIX_VPN"
CHANNEL_LINK = "https://t.me/MAGAMIX_VPN"

TARIFS = {
    "✨7 дней": (7, 50),
    "✨1 мес": (30, 150),
    "✨3 мес": (90, 350),
    "✨6 мес": (180, 600),
    "✨12 мес": (365, 1000)
}

STARS_PRICES = {    # примерные цены в Stars (можно подкорректировать под реальный курс)
    "✨7 дней": 30,
    "✨1 мес": 85,
    "✨3 мес": 200,
    "✨6 мес": 350,
    "✨12 мес": 580,
}

HAPP_LINKS = {
    "Android": "https://play.google.com/store/apps/details?id=com.happproxy&hl=ru&pli=1",
    "iOS": "https://apps.apple.com/ru/app/happ-proxy-utility-plus/id6746188973",
    "Windows": "https://github.com/Happ-proxy/happ-desktop/releases/latest/download/setup-Happ.x64.exe",
    "MacOS": "https://apps.apple.com/ru/app/happ-proxy-utility-plus/id6746188973"
}

PAYMENT_METHODS = {
    "stars": "⭐ Оплата звёздами Telegram",
    "yookassa": "💳 Карта · СБП · ЮMoney"
}

bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

class States(StatesGroup):
    waiting_free_check = State()

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
        "usage_limit_GB": 150,
        "mode": "no_reset"
    }
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=15)
        response.raise_for_status()
        data = response.json()
        uuid = data.get("uuid")
        if uuid:
            # Сохраняем в БД
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            c.execute("INSERT INTO subscriptions (user_id, uuid, days, created_at, status) VALUES (?, ?, ?, ?, ?)",
                      (user_id, uuid, days, created_at, "active"))
            conn.commit()
            conn.close()

            profile_link = f"{HIDDIFY_CLIENT_PATH}/{uuid}/"
            return f"{DEEPLINK_BASE}{profile_link}"
        return None
    except Exception as e:
        logging.error(f"Ошибка API: {e}")
        return None

def update_hiddify_user_days(uuid: str, new_total_days: int) -> bool:
    url = f"{HIDDIFY_ADMIN_PATH}/api/v2/admin/user/{uuid}/"
    headers = {
        "Hiddify-API-Key": API_KEY,
        "Content-Type": "application/json"
    }
    payload = {
        "package_days": new_total_days
        # Можно добавить: "mode": "no_reset" если нужно сохранить режим
    }
    
    try:
        response = requests.patch(url, headers=headers, json=payload, timeout=15)
        # Или попробуй PUT, если PATCH не сработает: requests.put(...)
        
        response.raise_for_status()  # кинет исключение при 4xx/5xx
        
        data = response.json()
        logging.info(f"Успешно обновлено package_days для {uuid}: {data}")
        return True
    
    except requests.exceptions.HTTPError as e:
        logging.error(f"HTTP ошибка при обновлении {uuid}: {e.response.status_code} - {e.response.text}")
        return False
    except Exception as e:
        logging.error(f"Общая ошибка обновления {uuid}: {e}")
        return False

def tarifs_menu():
    kb = []
    for name, (days, price) in TARIFS.items():
        text = f"{name} — {price}₽"
        if days > 30:
            monthly = round(price / (days / 30))
            text += f"  ({monthly}₽/мес)"
        kb.append([InlineKeyboardButton(text=text, callback_data=f"tarif_{name}")])
    
    kb.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")])
    
    return InlineKeyboardMarkup(inline_keyboard=kb)


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

async def give_referral_bonus(referrer_id: int, referred_user_id: int):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    c.execute("""
        SELECT id, uuid, days, created_at 
        FROM subscriptions 
        WHERE user_id = ? AND status = 'active'
        ORDER BY created_at DESC 
        LIMIT 1
    """, (referrer_id,))
    existing = c.fetchone()

    days_to_add = 3
    success = False

    if existing:
        sub_id, uuid, current_days, created_at = existing
        new_days = current_days + days_to_add
        
        # Пытаемся обновить в Hiddify
        if update_hiddify_user_days(uuid, new_days):
            # Успех → обновляем БД
            c.execute("UPDATE subscriptions SET days = ? WHERE id = ?", (new_days, sub_id))
            success = True
            await bot.send_message(
                ADMIN_ID,
                f"Реферал от {referred_user_id} → +{days_to_add} дней (продление в Hiddify) для {referrer_id}. Новый total: {new_days}"
            )
        else:
            await bot.send_message(ADMIN_ID, f"❌ Не удалось продлить в Hiddify для {referrer_id} (uuid: {uuid})")
    else:
        # Создаём новую — как раньше
        deeplink = create_hiddify_user(days_to_add, referrer_id)
        if deeplink:
            success = True
    
    conn.commit()
    conn.close()
    

# Старт
@dp.message(Command("start"))
async def start(message: Message):
    user_id = message.from_user.id
    username = message.from_user.username or "нет"
    name = message.from_user.first_name

    # Проверяем, есть ли реферальный параметр
    args = message.text.split()
    referrer_id = None
    if len(args) > 1 and args[1].startswith("ref_"):
        try:
            referrer_id = int(args[1].split("_")[1])
            if referrer_id == user_id:
                referrer_id = None  # сам на себя не реферит
        except:
            referrer_id = None

    # Добавляем пользователя, если новый
    is_new = add_user_if_new(user_id, username)

    if is_new and referrer_id:
        await give_referral_bonus(referrer_id, user_id)

        try:
            await bot.send_message(
                referrer_id,
                "🎉 Новый друг по твоей ссылке! +3 дня к подписке добавлено!"
            )
        except:
            pass 

    # Обычное приветствие
    await send_main_menu(message, name, user_id)

# Оплата
@dp.callback_query(F.data == "pay")
async def pay(callback: CallbackQuery):
    await callback.message.edit_text("💸 Выбери тариф:", reply_markup=tarifs_menu())


@dp.callback_query(F.data.startswith("tarif_"))
async def tarif_chosen(callback: CallbackQuery, state: FSMContext):
    tarif_name = callback.data.split("_", 1)[1]
    
    if tarif_name not in TARIFS:
        await callback.answer("Такой тариф не найден", show_alert=True)
        return
        
    days, rub_price = TARIFS[tarif_name]
    stars_price = STARS_PRICES.get(tarif_name, rub_price // 6)  # запасной вариант
    
    await state.update_data(
        tarif=tarif_name,
        days=days,
        rub_price=rub_price,
        stars_price=stars_price
    )
    
    text = (
        f"Вы выбрали тариф **{tarif_name}** \n\n"
        f"Стоимость: **{rub_price} ₽**\n\n"
        "Выберите удобный способ оплаты:"
    )
    
    kb = []
    for method_key, method_title in PAYMENT_METHODS.items():
        if method_key == "stars":
            button_text = f"Оплата звёздами ({stars_price})"
        else:
            button_text = method_title
            
        kb.append([InlineKeyboardButton(
            text=button_text,
            callback_data=f"pay_{method_key}_{tarif_name}"
        )])
    
    kb.append([InlineKeyboardButton(text="🔙 Назад к тарифам", callback_data="pay")])
    
    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb),
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("pay_stars_"))
async def pay_with_stars(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    tarif_name = callback.data.split("_", 2)[2]
    days = data["days"]
    stars_amount = data["stars_price"]

    prices = [LabeledPrice(label=f"Подписка {tarif_name}", amount=stars_amount)]

    try:
        invoice = await bot.send_invoice(
            chat_id=callback.message.chat.id,
            title=f"Magam VPN — {tarif_name}",
            description=f"Доступ к премиум VPN на {days} дней",
            payload=f"vpn_{callback.from_user.id}_{tarif_name}_{days}",  # уникальный payload
            provider_token="",  # для Stars оставляем пустым!
            currency="XTR",
            prices=prices,
            need_name=False,
            need_phone_number=False,
            need_email=False,
            need_shipping_address=False,
            is_flexible=False,
            reply_markup=None  # Telegram сам покажет кнопку Pay
        )

        await callback.answer("Счёт выставлен! Оплатите ⭐ звёздами", show_alert=False)

    except Exception as e:
        logging.error(f"Ошибка отправки Stars invoice: {e}")
        await callback.message.edit_text("❌ Не удалось создать счёт. Попробуйте позже или выберите другой способ.")

# ----------------------------------------------------------------------
#                     ОПЛАТА ЧЕРЕЗ ЮKASSA
# ----------------------------------------------------------------------
@dp.callback_query(F.data.startswith("pay_yookassa_"))
async def pay_yookassa(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    tarif_name = callback.data.split("_", 2)[2]
    days = data["days"]
    amount = data["rub_price"]
   
    try:
        payment = Payment.create({
            "amount": {
                "value": f"{amount}.00",
                "currency": "RUB"
            },
            "confirmation": {
                "type": "redirect",
                "return_url": "https://t.me/MAGAMIX_VPN"
            },
            "capture": True,
            "description": f"Magam VPN — {tarif_name} | User {callback.from_user.id}",
            "metadata": {
                "user_id": str(callback.from_user.id),
                "tarif": tarif_name,
                "source": "telegram_bot"
            },
            "receipt": {
                "customer": {
                    "email": "mohammadakubov@gmail.com"
                },
                "items": [
                    {
                        "description": f"Подписка Magam VPN — {tarif_name}",
                        "quantity": 1,
                        "amount": {
                            "value": f"{amount}.00",
                            "currency": "RUB"
                        },
                        "vat_code": 1,  # или 3, если НДС 0%
                        "payment_mode": "full_prepayment",
                        "payment_subject": "service"
                    }
                ]
            }
        })
       
        payment_url = payment.confirmation.confirmation_url
       
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💳 Оплатить сейчас", url=payment_url)],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="pay")]
        ])
       
        text = (
            f"Оплата через ЮKassa\n\n"
            f"Тариф: **{tarif_name}**\n"  # без дней, как ты хотел
            f"Сумма: **{amount} ₽**\n\n"
            "Нажмите кнопку ниже для перехода к оплате 👇"
        )
       
        await callback.message.edit_text(
            text,
            reply_markup=kb,
            parse_mode="Markdown"
        )
       
    except Exception as e:
        logging.error(f"Ошибка создания платежа ЮKassa: {e}")
        await callback.message.edit_text("❌ Не удалось создать платёж. Попробуйте позже или напишите в поддержку.")
   
    await callback.answer()



@dp.pre_checkout_query()
async def pre_checkout_handler(pre_checkout_query: PreCheckoutQuery):
    # Здесь можно проверить payload, наличие товара и т.д.
    # Для простоты всегда подтверждаем
    await bot.answer_pre_checkout_query(
        pre_checkout_query_id=pre_checkout_query.id,
        ok=True
    )

@dp.pre_checkout_query()
async def pre_checkout_handler(pre_checkout_query: PreCheckoutQuery):
    # Здесь можно проверить payload, наличие товара и т.д.
    # Для простоты всегда подтверждаем
    await bot.answer_pre_checkout_query(
        pre_checkout_query_id=pre_checkout_query.id,
        ok=True
    )


# Успешная оплата — САМОЕ ВАЖНОЕ!
@dp.message(F.successful_payment)
async def successful_stars_payment(message: types.Message):
    payment = message.successful_payment
    user_id = message.from_user.id
    
    # Разбираем payload
    try:
        _, uid_str, tarif_name, days_str = payment.invoice_payload.split("_")
        days = int(days_str)
    except:
        days = 7  # fallback
        
    # Выдаём подписку
    deeplink = create_hiddify_user(days, user_id)
    
    if deeplink:
        text = (
            f"🎉 Оплата через ⭐ Stars прошла успешно!\n\n"
            f"Ваша подписка на **{days} дней** активирована!\n"
            f"Сумма: {payment.total_amount} ⭐\n\n"
            f"Перейдите в «Установить VPN» в главном меню"
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📲 Главное меню", callback_data="back_main")]
        ])
        
        await message.answer(text, reply_markup=kb, parse_mode="Markdown")
        
        # Уведомление админу
        await bot.send_message(
            ADMIN_ID,
            f"⭐ НОВАЯ ОПЛАТА Stars!\n"
            f"Пользователь: {message.from_user.id} (@{message.from_user.username or 'нет'})\n"
            f"Тариф: {tarif_name} | {days} дней | {payment.total_amount} ⭐"
        )
    else:
        await message.answer("✅ Оплата прошла, но ошибка выдачи доступа. Напишите в поддержку.")





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
                deeplink = create_hiddify_user(3, callback.from_user.id)
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
    
    if not subs:
        text = "У тебя нет активных подписок.\n\nОформи тариф или возьми 3 дня бесплатно!"
        kb = [
            [InlineKeyboardButton(text="💳 Оплатить VPN", callback_data="pay")],
            [InlineKeyboardButton(text="🎁 Бесплатно 3 дня", callback_data="free_3days")],
            [InlineKeyboardButton(text="🔙 Главное меню", callback_data="back_main")]
        ]
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
        return

    # Есть подписки
    import random
    
    text = "🗝️Ваши активные подписки:\n\n✅Нажмите для установки"
    
    kb = []
    
    for uuid, days, created_at in subs:
        fake_code = random.randint(100000, 999999)
        button_text = f"🗝️{fake_code} ({days} дней)"
        
        kb.append([InlineKeyboardButton(
            text=button_text,
            callback_data=f"select_device_{uuid}"
        )])

    
    kb.append([InlineKeyboardButton(text="🔙 Главное меню", callback_data="back_main")])
    
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@dp.callback_query(F.data.startswith("select_device_"))
async def select_device(callback: CallbackQuery):
    try:
        _, uuid = callback.data.split("_", 1)
    except:
        uuid = None

    text = "Выберите свое устройство ниже для получения инструкции:"
   
    kb = [
        [InlineKeyboardButton(text="📱 Android",   callback_data=f"device_Android_{uuid or ''}")],
        [InlineKeyboardButton(text="🍎 iOS",       callback_data=f"device_iOS_{uuid or ''}")],
        [InlineKeyboardButton(text="🖥️ Windows",  callback_data=f"device_Windows_{uuid or ''}")],
        [InlineKeyboardButton(text="💻 MacOS",     callback_data=f"device_MacOS_{uuid or ''}")],
        [InlineKeyboardButton(text="🔙 Главное меню", callback_data="back_main")]
    ]
   
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    await callback.answer()

@dp.callback_query(F.data.startswith("device_"))
async def device_instruction(callback: CallbackQuery):
    try:
        parts = callback.data.split("_", 2)
        platform = parts[1]
        uuid = parts[2] if len(parts) > 2 and parts[2] else None
    except:
        platform = "Android"
        uuid = None

    user_id = callback.from_user.id

    if uuid:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute(
            "SELECT uuid, days FROM subscriptions WHERE user_id = ? AND uuid = ? AND status = 'active'",
            (user_id, uuid)
        )
        sub = c.fetchone()
        conn.close()
        if sub:
            selected_uuid = sub[0]
        else:
            selected_uuid = None
    else:
        selected_uuid = None

    # Если uuid не найден или не передан — берём первую подписку как fallback
    if not selected_uuid:
        subs = get_user_subscriptions(user_id)
        if not subs:
            await callback.message.edit_text("Подписка не найдена. Обратитесь в поддержку.")
            return
        selected_uuid, _, _ = subs[0]

    deeplink = f"{DEEPLINK_BASE}{HIDDIFY_CLIENT_PATH}/{selected_uuid}/"

    text = (
        "✅ Скачайте и установите приложение Happ нажав на первую кнопку ниже «🔗Скачать приложение»\n\n"
        "✅ Вставьте свою подписку в приложение нажав на вторую кнопку ниже «🗝️Добавить подписку»\n\n"
        "⚡ Нажмите на большую кнопку в приложении Happ и наслаждайтесь скоростью."
    )
   
    kb = [
        [InlineKeyboardButton(text="🔗 Скачать приложение", url=HAPP_LINKS.get(platform, HAPP_LINKS["Android"]))],
        [InlineKeyboardButton(text="🗝️ Добавить подписку", url=deeplink)],
        [InlineKeyboardButton(text="🔙 Главное меню", callback_data="back_main")]
    ]
   
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    await callback.answer()
    
        
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

@dp.message(Command("checkpay"))
async def checkpay_handler(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("Только админ может использовать эту команду")
        return

    args = message.text.split()
    if len(args) < 2:
        await message.answer("Использование: /checkpay <payment_id>\nПример: /checkpay 30faf05a-000f-5001-8000-1b73bbd53011")
        return

    payment_id = args[1]
    try:
        payment = Payment.find_one(payment_id)
        status = payment.status
        await message.answer(f"Статус платежа {payment_id}: **{status}**")

        if status == "succeeded":
            user_id = int(payment.metadata["user_id"])
            days = int(payment.metadata.get("days", 7))  # ← fallback 7 дней
            tarif = payment.metadata.get("tarif", "неизвестно")
            amount = payment.amount.value

            deeplink = create_hiddify_user(days, user_id)
            if deeplink:
                await bot.send_message(
                    user_id,
                    f"🎉 Оплата прошла успешно! (ручная проверка)\n\n"
                    f"Тариф: **{tarif}** — {days} дней\n"
                    f"Сумма: {amount} ₽\n\n"
                    "Перейди в меню → «Установить VPN»"
                )
                await message.answer(f"Успех! Подписка выдана пользователю {user_id} на {days} дней")
            else:
                await message.answer(f"Платёж успешен, но ошибка выдачи подписки для {user_id}")

        elif status == "pending":
            await message.answer("Платёж ещё в обработке (pending)")
        else:
            await message.answer(f"Платёж не успешен (статус: {status})")

    except Exception as e:
        await message.answer(f"Ошибка проверки платежа: {str(e)}")


async def yookassa_webhook(request):
    try:
        event = await request.json()
        logging.info(f"Получен webhook от ЮKassa: {event}")
        if event.get('event') == 'payment.succeeded':
            payment = event['object']
            user_id = int(payment['metadata']['user_id'])
            days = int(payment['metadata']['days'])
            tarif = payment['metadata'].get('tarif', 'неизвестно')
            amount = payment['amount']['value']

            deeplink = create_hiddify_user(days, user_id)
            if deeplink:
                await bot.send_message(
                    user_id,
                    f"🎉 Оплата через ЮKassa прошла успешно!\n\n"
                    f"Тариф: **{tarif}** \n"
                    f"Сумма: {amount} ₽\n\n"
                    "Перейди в меню → «Установить VPN»"
                )
                await bot.send_message(
                    ADMIN_ID,
                    f"ЮKassa успех: пользователь {user_id} | {tarif} | {days} дней | {amount}₽"
                )
            else:
                await bot.send_message(ADMIN_ID, f"ЮKassa успех, но ошибка выдачи подписки: {user_id}")

        return web.Response(status=200)
    except Exception as e:
        logging.error(f"Webhook ошибка: {e}")
        return web.Response(status=200)

async def start_webhook_server():
    app = web.Application()
    app.router.add_post('/bot-yookassa-webhook', yookassa_webhook)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8081)
    await site.start()
    print("Webhook сервер запущен на порту 8081")

async def main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Главное меню", callback_data="back_main")]
    ])


async def main():
    logging.basicConfig(level=logging.INFO)
    print("🚀 Бот запущен")
    await start_webhook_server()
    await dp.start_polling(
        bot,
        drop_pending_updates=True
    )

if __name__ == "__main__":
    asyncio.run(main())
