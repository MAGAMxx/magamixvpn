import asyncio
import logging
import sqlite3
import requests
from datetime import datetime, timedelta
import random
from aiogram import Bot, Dispatcher, types, F, Router
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



# Нидерланды (основная панель)
HIDDIFY_ADMIN_PATH_NL = "https://vpn.tgflovv.ru/a2NRdl78IHwZBYBReUx"
HIDDIFY_CLIENT_PATH_NL = "https://vpn.tgflovv.ru/6bqCF1dLYRFoerALhhXu8cn98"
API_KEY_NL = "245320ca-f07d-401b-9f43-000735d93085"
# Германия (вторая панель)
HIDDIFY_ADMIN_PATH_DE = "https://de.vpn.tgflovv.ru/PD6KuWi6xGGguNRRz3v"  # замени на реальный
HIDDIFY_CLIENT_PATH_DE = "https://de.vpn.tgflovv.ru/nm4cYxIzEFEwvbnvo2bpaChEUgYIv8"
API_KEY_DE = "cc90cb5a-2a17-4ec6-ac90-6c92f8bdce1c"  # если отличается

DEEPLINK_BASE = "https://deeplink.website/link?url_ha="

CHANNEL_USERNAME = "@MAGAMIX_VPN"
CHANNEL_LINK = "https://t.me/MAGAMIX_VPN"

TARIFS = {
    "✨7 дней": (7, 10),
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


admin_router = Router()

# Глобальный фильтр: только от админа
admin_router.message.filter(lambda message: message.from_user.id == ADMIN_ID)
admin_router.callback_query.filter(lambda callback: callback.from_user.id == ADMIN_ID)


bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
dp.include_router(admin_router)

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
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            payment_id TEXT UNIQUE,
            tarif TEXT,
            days INTEGER,
            created_at TEXT,
            status TEXT DEFAULT 'pending'
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            uuid TEXT UNIQUE,
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

def create_or_extend_both(added_days: int, user_id: int, existing_uuid: str = None) -> dict | None:
    uuid = existing_uuid or str(uuid4())
    
    def process_server(base_url, api_key, client_path, server_name=""):
        nonlocal uuid
        headers = {"Hiddify-API-Key": api_key, "Content-Type": "application/json"}
        is_new = not existing_uuid
        
        if is_new:
            url = f"{base_url}/api/v2/admin/user/"
            payload = {
                "name": f"tg_{user_id}",
                "package_days": added_days,
                "usage_limit_GB": 150,
                "mode": "no_reset"
            }
            if server_name == "DE":
                payload["uuid"] = uuid
            
            try:
                r = requests.post(url, json=payload, headers=headers, timeout=15)
                r.raise_for_status()
                if server_name == "NL":
                    new_uuid = r.json().get("uuid")
                    if new_uuid:
                        uuid = new_uuid
                return True
            except Exception as e:
                logging.error(f"Ошибка создания на {server_name}: {e}")
                return False
        
        else:
            url = f"{base_url}/api/v2/admin/user/{uuid}/"
            try:
                r_get = requests.get(url, headers=headers, timeout=10)
                if r_get.status_code == 404:
                    return process_server(base_url, api_key, client_path, server_name)
                r_get.raise_for_status()
                data = r_get.json()
                current_package = data.get("package_days", 0)
                start_date_str = data.get("start_date")
                remaining = 0
                if start_date_str and start_date_str != "null":
                    start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
                    remaining = (start_date + timedelta(days=current_package) - datetime.now()).days
                new_package_days = current_package + added_days if remaining > 0 else added_days
                payload = {
                    "package_days": new_package_days,
                    "name": f"tg_{user_id}",
                    "usage_limit_GB": 150,
                    "mode": "no_reset"
                }
                r_patch = requests.patch(url, json=payload, headers=headers, timeout=12)
                r_patch.raise_for_status()
                return True
            except Exception as e:
                logging.error(f"Ошибка продления на {server_name} (uuid {uuid}): {e}")
                return False
    
    if not process_server(HIDDIFY_ADMIN_PATH_NL, API_KEY_NL, HIDDIFY_CLIENT_PATH_NL, "NL"):
        return None
    
    process_server(HIDDIFY_ADMIN_PATH_DE, API_KEY_DE, HIDDIFY_CLIENT_PATH_DE, "DE")
    
    if not existing_uuid:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        logging.info(f"ВСТАВКА НОВОЙ ПОДПИСКИ: user={user_id}, uuid={uuid}, created_at={created_at}, status=active")
        c.execute("""
            INSERT INTO subscriptions (user_id, uuid, created_at, status)
            VALUES (?, ?, ?, ?)
        """, (user_id, uuid, created_at, "active"))
        conn.commit()
        
        # Проверяем сразу после вставки
        c.execute("SELECT status FROM subscriptions WHERE uuid = ?", (uuid,))
        status_after = c.fetchone()[0]
        logging.info(f"СТАТУС СРАЗУ ПОСЛЕ ВСТАВКИ: {status_after}")
        
        conn.close()
    
    return {
        "nl": f"{DEEPLINK_BASE}{HIDDIFY_CLIENT_PATH_NL}/{uuid}/",
        "de": f"{DEEPLINK_BASE}{HIDDIFY_CLIENT_PATH_DE}/{uuid}/",
        "uuid": uuid
    }

def delete_hiddify_user(uuid: str, base_url: str, api_key: str) -> bool:
    """
    Удаляет пользователя в Hiddify по UUID.
    Возвращает True если успешно.
    """
    url = f"{base_url}/api/v2/admin/user/{uuid}/"
    headers = {"Hiddify-API-Key": api_key, "Content-Type": "application/json"}
    
    try:
        r = requests.delete(url, headers=headers, timeout=10)
        if r.status_code in (200, 204, 404):  # 404 тоже ок — уже удалён
            logging.info(f"Пользователь {uuid} удалён на {base_url}")
            return True
        else:
            logging.error(f"Ошибка удаления {uuid} на {base_url}: {r.status_code} {r.text}")
            return False
    except Exception as e:
        logging.error(f"Исключение при удалении {uuid} на {base_url}: {e}")
        return False

def cleanup_expired_subscriptions(user_id: int) -> None:
    subs = get_user_subscriptions(user_id)
    if not subs:
        return
    
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    for uuid, created_at in subs:
        created_at_dt = datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S")
        age_minutes = (datetime.now() - created_at_dt).total_seconds() / 60
        
        # Если подписка младше 5 минут — не трогаем, даём Hiddify время
        if age_minutes < 5:
            logging.info(f"Подписка {uuid} новая ({age_minutes:.1f} мин) — пропускаем очистку")
            continue
        
        remaining = get_remaining_days(uuid)
        if remaining <= 0:
            delete_hiddify_user(uuid, HIDDIFY_ADMIN_PATH_NL, API_KEY_NL)
            delete_hiddify_user(uuid, HIDDIFY_ADMIN_PATH_DE, API_KEY_DE)
            
            c.execute("UPDATE subscriptions SET status = 'expired' WHERE uuid = ? AND user_id = ?",
                      (uuid, user_id))
            logging.info(f"Подписка {uuid} для user {user_id} истекла и помечена как expired")
    
    conn.commit()
    conn.close()

def get_remaining_days(uuid: str) -> int:
    # Сначала NL
    remaining = _get_remaining_from_server(uuid, HIDDIFY_ADMIN_PATH_NL, API_KEY_NL)
    if remaining > 0:
        return remaining
    # Если NL не дал — DE
    return _get_remaining_from_server(uuid, HIDDIFY_ADMIN_PATH_DE, API_KEY_DE)


def _get_remaining_from_server(uuid: str, base_url: str, api_key: str) -> int:
    url = f"{base_url}/api/v2/admin/user/{uuid}/"
    headers = {"Hiddify-API-Key": api_key, "Content-Type": "application/json"}
    try:
        r = requests.get(url, headers=headers, timeout=10)
        r.raise_for_status()
        data = r.json()
        package_days = data.get("package_days", 0)
        start_date_str = data.get("start_date")
        if not start_date_str or start_date_str == "null":
            return 0
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
        expiry_date = start_date + timedelta(days=package_days)
        today = datetime.now().date()
        remaining = (expiry_date.date() - today).days
        return max(0, remaining)
    except Exception as e:
        logging.error(f"Ошибка получения дней для {uuid} на {base_url}: {e}")
        return 0

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
    c.execute("SELECT uuid, created_at FROM subscriptions WHERE user_id = ? AND status = 'active'", (user_id,))
    subs = c.fetchall()
    conn.close()
    return subs

async def give_referral_bonus(referrer_id: int, referred_user_id: int):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        SELECT uuid, created_at
        FROM subscriptions
        WHERE user_id = ? AND status = 'active'
        ORDER BY created_at DESC
        LIMIT 1
    """, (referrer_id,))
    existing = c.fetchone()
    
    added_days = 3
    
    if existing:
        uuid = existing[0]
        result = create_or_extend_both(added_days=added_days, user_id=referrer_id, existing_uuid=uuid)
    else:
        result = create_or_extend_both(added_days=added_days, user_id=referrer_id)
    
    if result:
        await bot.send_message(
            ADMIN_ID,
            f"Реферал от {referred_user_id} → +{added_days} дней на обоих серверах для {referrer_id}"
        )
    else:
        await bot.send_message(ADMIN_ID, f"❌ Не удалось выдать реферальные дни {referrer_id}")
    
    conn.commit()
    conn.close()

def extend_or_create_subscription(user_id: int, added_days: int) -> dict | None:
    subs = get_user_subscriptions(user_id)
    if subs:
        uuid = subs[0][0]
        logging.info(f"Продлеваем существующую подписку для user {user_id}, uuid {uuid}, добавляем {added_days} дней")
        result = create_or_extend_both(added_days=added_days, user_id=user_id, existing_uuid=uuid)
    else:
        logging.info(f"Создаём новую подписку для user {user_id}, на {added_days} дней")
        result = create_or_extend_both(added_days=added_days, user_id=user_id)
    
    return result


async def cleanup_all_expired():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT DISTINCT user_id FROM subscriptions WHERE status = 'active'")
    user_ids = [row[0] for row in c.fetchall()]
    conn.close()
    
    for uid in user_ids:
        cleanup_expired_subscriptions(uid)
    

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
                "days": str(days),
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
        payment_id = payment.id
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("INSERT INTO payments (user_id, payment_id, tarif, days, created_at) VALUES (?, ?, ?, ?, ?)",
                  (callback.from_user.id, payment_id, tarif_name, days, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        conn.close()
       
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


# Успешная оплата — САМОЕ ВАЖНОЕ!
@dp.message(F.successful_payment)
async def successful_stars_payment(message: types.Message):
    payment = message.successful_payment
    user_id = message.from_user.id
   
    try:
        _, uid_str, tarif_name, days_str = payment.invoice_payload.split("_")
        days = int(days_str)
    except:
        days = 7  # fallback
       
    result = extend_or_create_subscription(user_id, days)
   
    if result:
        # Даём время Hiddify синхронизировать данные
        await asyncio.sleep(10)
        
        text = (
            f"🎉 Оплата через ⭐ Stars прошла успешно!\n\n"
            f"Добавлено **+{days} дней** к подписке!\n"
            f"Сумма: {payment.total_amount} ⭐\n\n"
            f"Перейдите в «Установить VPN» → добавьте Германию и/или Нидерланды"
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📲 Главное меню", callback_data="back_main")]
        ])
       
        await message.answer(text, reply_markup=kb, parse_mode="Markdown")
       
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
                result = create_or_extend_both(3, callback.from_user.id)
                if result:
                    await callback.message.edit_text(
                        "🎉 Подписка на 3 дня выдана на обоих серверах!\n\n"
                        "Перейдите в «Установить VPN» → добавьте Германию и/или Нидерланды"
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
    
    # Сначала чистим истёкшие подписки
    cleanup_expired_subscriptions(user_id)
    
    subs = get_user_subscriptions(user_id)
    
    if not subs:
        text = "У тебя нет активных подписок.\n\nОформи тариф или пригласи друзей!"
        kb = [
            [InlineKeyboardButton(text="💳 Оплатить VPN", callback_data="pay")],
            [InlineKeyboardButton(text="👥 Пригласить друзей", callback_data="referral")],
            [InlineKeyboardButton(text="🔙 Главное меню", callback_data="back_main")]
        ]
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
        return
    
    text = "🗝️Ваши активные подписки:\n\n✅Нажмите для установки"
    warning_text = ""
    
    kb = []
    
    has_last_day = False
    
    for uuid, created_at in subs:
        remaining_days = get_remaining_days(uuid)
        
        if remaining_days == 1:
            has_last_day = True
        elif remaining_days <= 0:
            # На всякий случай ещё раз пометим (хотя cleanup уже должен был)
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute("UPDATE subscriptions SET status = 'expired' WHERE uuid = ?", (uuid,))
            conn.commit()
            conn.close()
            continue  # не показываем истёкшие
        
        fake_code = random.randint(100000, 999999)
        button_text = f"🗝️{fake_code} ({remaining_days} дней)"
        kb.append([InlineKeyboardButton(
            text=button_text,
            callback_data=f"select_device_{uuid}"
        )])
    
    # Добавляем предупреждение, если есть подписка на 1 день
    if has_last_day:
        warning_text = "\n\n⚠️ У одной из подписок остался **последний день**!\nРекомендуем продлить заранее."
        kb.insert(0, [InlineKeyboardButton(text="💳 Продлить подписку", callback_data="pay")])
    
    kb.append([InlineKeyboardButton(text="🔙 Главное меню", callback_data="back_main")])
    
    full_text = text + warning_text
    
    await callback.message.edit_text(full_text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

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

    # Получаем выбранный UUID или fallback
    if uuid:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute(
            "SELECT uuid FROM subscriptions WHERE user_id = ? AND uuid = ? AND status = 'active'",
            (user_id, uuid)
        )
        sub = c.fetchone()
        conn.close()
        selected_uuid = sub[0] if sub else None
    else:
        selected_uuid = None

    if not selected_uuid:
        subs = get_user_subscriptions(user_id)
        if not subs:
            await callback.message.edit_text("Подписка не найдена. Обратитесь в поддержку.")
            return
        selected_uuid = subs[0][0]  # берём первый активный UUID

    # Формируем обе ссылки
    deeplink_nl = f"{DEEPLINK_BASE}{HIDDIFY_CLIENT_PATH_NL}/{selected_uuid}/"
    deeplink_de = f"{DEEPLINK_BASE}{HIDDIFY_CLIENT_PATH_DE}/{selected_uuid}/"

    text = (
        "✅ Скачайте приложение Happ\n\n"
        "Затем добавьте подписку на нужный сервер (можно оба):\n\n"
        "🇩🇪 Германия — максимальная скорость\n"
        "🇳🇱 Нидерланды — стабильность и обход\n\n"
        "В Happ переключайся между ними в один клик!"
    )

    kb = [
        [InlineKeyboardButton(text="🔗 Скачать Happ", url=HAPP_LINKS.get(platform, HAPP_LINKS["Android"]))],
        [InlineKeyboardButton(text="🇩🇪 Добавить Германию", url=deeplink_de)],
        [InlineKeyboardButton(text="🇳🇱 Добавить Нидерланды", url=deeplink_nl)],
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

            deeplink = extend_or_create_subscription(user_id, days)
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

# ================== АДМИН-ПАНЕЛЬ ==================
class AdminStates(StatesGroup):
    waiting_for_user_id_or_username = State()
    waiting_for_days = State()
    waiting_for_broadcast_text = State()

# Вспомогательная функция для кнопки "Назад в админку"
def admin_back_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад в админ-панель", callback_data="admin_back")]
    ])

# Теперь хендлеры без внутренней проверки
@admin_router.message(Command("admin"))
async def admin_panel(message: Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton(text="➕ Добавить дни пользователю", callback_data="admin_add_days")],
        [InlineKeyboardButton(text="📢 Рассылка всем", callback_data="admin_broadcast")],
        [InlineKeyboardButton(text="❌ Закрыть", callback_data="admin_close")]
    ])
    await message.answer("👑 Админ-панель", reply_markup=kb)

@admin_router.callback_query(F.data == "admin_back")
async def admin_back(callback: CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton(text="➕ Добавить дни пользователю", callback_data="admin_add_days")],
        [InlineKeyboardButton(text="📢 Рассылка всем", callback_data="admin_broadcast")],
        [InlineKeyboardButton(text="❌ Закрыть", callback_data="admin_close")]
    ])
    await callback.message.edit_text("👑 Админ-панель", reply_markup=kb)
    await callback.answer()

@admin_router.callback_query(F.data == "admin_close")
async def admin_close(callback: CallbackQuery):
    await callback.message.delete()
    await callback.answer("Панель закрыта")

# 1. Статистика
@admin_router.callback_query(F.data == "admin_add_days")
async def admin_add_days_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "Введите user_id или @username пользователя:",
        reply_markup=admin_back_kb()
    )
    await state.set_state(AdminStates.waiting_for_user_id_or_username)
    await callback.answer()

@admin_router.message(AdminStates.waiting_for_user_id_or_username)
async def process_user_identifier(message: Message, state: FSMContext):
    text = message.text.strip()
    
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    user_id = None
    
    if text.startswith('@'):
        username = text[1:].lower()
        c.execute("SELECT user_id FROM users WHERE LOWER(username) = ?", (username,))
        result = c.fetchone()
        if result:
            user_id = result[0]
    else:
        try:
            user_id = int(text)
            c.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
            if c.fetchone():
                pass
            else:
                user_id = None
        except ValueError:
            user_id = None
    
    conn.close()
    
    if user_id:
        await state.update_data(target_user_id=user_id)
        await message.answer(
            f"Пользователь найден (ID: {user_id})\n\nВведите количество дней для добавления:",
            reply_markup=admin_back_kb()
        )
        await state.set_state(AdminStates.waiting_for_days)
    else:
        await message.answer("Пользователь не найден. Попробуйте снова (ID или @username):", reply_markup=admin_back_kb())

@admin_router.message(AdminStates.waiting_for_days)
async def process_days_to_add(message: Message, state: FSMContext):
    try:
        days = int(message.text.strip())
        if days <= 0:
            raise ValueError
    except ValueError:
        await message.answer("Введите положительное число дней:", reply_markup=admin_back_kb())
        return
    
    data = await state.get_data()
    user_id = data['target_user_id']
    
    result = extend_or_create_subscription(user_id, days)
    
    if result:
        await bot.send_message(
            user_id,
            f"Админ добавил вам **+{days} дней** к подписке на обоих серверах! 🎁\n\n"
            "Проверьте в меню → «Установить VPN»"
        )
        await message.answer(
            f"Успех! Добавлено {days} дней пользователю {user_id}\n\n"
            f"UUID: {result['uuid']}\n"
            f"Нидерланды: {result['nl']}\n"
            f"Германия: {result['de']}",
            reply_markup=admin_back_kb(),
            parse_mode="Markdown"
        )
        await bot.send_message(
            ADMIN_ID,
            f"[Админ] Добавлено {days} дней пользователю {user_id} на оба сервера"
        )
    else:
        await message.answer("Ошибка при добавлении дней. Проверьте логи.")
    
    await state.clear()


@admin_router.callback_query(F.data == "admin_broadcast")
async def admin_broadcast_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "Введите текст сообщения для рассылки (можно с Markdown, эмодзи).\n\n"
        "После отправки — подтвердите рассылку.",
        reply_markup=admin_back_kb()
    )
    await state.set_state(AdminStates.waiting_for_broadcast_text)
    await callback.answer()

@admin_router.message(AdminStates.waiting_for_broadcast_text)
async def process_broadcast_text(message: Message, state: FSMContext):
    text = message.text.strip()
    
    if not text:
        await message.answer("Текст не может быть пустым. Введите сообщение:", reply_markup=admin_back_kb())
        return
    
    await state.update_data(broadcast_text=text)
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Отправить всем", callback_data="confirm_broadcast")],
        [InlineKeyboardButton(text="🔄 Изменить текст", callback_data="admin_broadcast")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")]
    ])
    
    await message.answer(
        f"Предпросмотр рассылки:\n\n{text}\n\n"
        f"Отправить это сообщение всем пользователям?",
        reply_markup=kb,
        parse_mode="Markdown"
    )
    await state.set_state(AdminStates.waiting_for_broadcast_text)

@admin_router.callback_query(F.data == "confirm_broadcast")
async def confirm_broadcast(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    broadcast_text = data.get('broadcast_text')
    
    if not broadcast_text:
        await callback.message.edit_text("Ошибка: текст рассылки не найден. Начните заново.", reply_markup=admin_back_kb())
        await state.clear()
        await callback.answer()
        return
    
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT user_id FROM users")
    users = c.fetchall()
    conn.close()
    
    total = len(users)
    success = 0
    failed = 0
    
    await callback.message.edit_text(
        f"Рассылка запущена...\n\nОтправлено: 0/{total}",
        reply_markup=admin_back_kb()
    )
    
    for i, (user_id,) in enumerate(users, 1):
        try:
            await bot.send_message(user_id, broadcast_text, parse_mode="Markdown")
            success += 1
            await asyncio.sleep(0.05)
        except Exception as e:
            logging.error(f"Ошибка отправки юзеру {user_id}: {e}")
            failed += 1
        
        if i % 20 == 0 or i == total:
            await callback.message.edit_text(
                f"Рассылка запущена...\n\n"
                f"Отправлено: {success}/{total} (успешно)\n"
                f"Ошибок: {failed}",
                reply_markup=admin_back_kb()
            )
    
    final_text = (
        f"Рассылка завершена!\n\n"
        f"Всего пользователей: {total}\n"
        f"Успешно отправлено: {success}\n"
        f"Не удалось отправить: {failed}\n\n"
        f"Текст рассылки:\n{broadcast_text}"
    )
    
    await callback.message.edit_text(final_text, reply_markup=admin_back_kb(), parse_mode="Markdown")
    await bot.send_message(ADMIN_ID, f"Рассылка завершена: {success}/{total}")
    await state.clear()
    await callback.answer("Рассылка завершена!")



async def main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Главное меню", callback_data="back_main")]
    ])

async def check_payments():
    while True:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT payment_id, user_id, tarif, days FROM payments WHERE status = 'pending'")
        payments = c.fetchall()
        for payment_id, user_id, tarif, days in payments:
            try:
                payment = Payment.find_one(payment_id)
                if payment.status == 'succeeded':
                    result = extend_or_create_subscription(user_id, days)
                    if result:
                        await bot.send_message(
                            user_id,
                            f"🎉 Оплата через ЮKassa прошла успешно!\n\n"
                            f"Тариф: **{tarif}** \n"
                            f"Сумма: {payment.amount.value} ₽\n\n"
                            "Подписка активирована на обоих серверах!\n"
                            "Перейди в меню → «Установить VPN»"
                        )
                        c.execute("UPDATE payments SET status = 'succeeded' WHERE payment_id = ?", (payment_id,))
                        conn.commit()
                    else:
                        await bot.send_message(user_id, "Оплата прошла, но ошибка выдачи ключа. Напиши в поддержку.")
                elif payment.status in ['canceled', 'refunded']:
                    c.execute("UPDATE payments SET status = ? WHERE payment_id = ?", (payment.status, payment_id))
                    conn.commit()
            except Exception as e:
                logging.error(f"Ошибка проверки платежа {payment_id}: {e}")
        conn.close()
        await asyncio.sleep(60)  # проверка каждую минуту

async def periodical_cleanup():
    """
    Периодически (раз в час) проверяет и удаляет все истёкшие подписки у всех пользователей.
    """
    while True:
        try:
            # Получаем всех пользователей с активными подписками
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute("SELECT DISTINCT user_id FROM subscriptions WHERE status = 'active'")
            user_ids = [row[0] for row in c.fetchall()]
            conn.close()

            # Чистим для каждого пользователя
            for uid in user_ids:
                cleanup_expired_subscriptions(uid)  # ← твоя функция из предыдущего ответа

            logging.info(f"Периодическая очистка завершена. Обработано пользователей: {len(user_ids)}")

        except Exception as e:
            logging.error(f"Ошибка в periodical_cleanup: {e}", exc_info=True)

        # Ждём 1 час (3600 секунд)
        await asyncio.sleep(3600)

async def main():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler("bot.log"),    # логи в файл
            logging.StreamHandler()            # и в консоль
        ]
    )
    
    print("🚀 Бот запущен")
    
    # Запускаем фоновые задачи
    asyncio.create_task(check_payments())
    asyncio.create_task(periodical_cleanup())  # ← новая задача очистки
    
    # Запускаем polling
    await dp.start_polling(
        bot,
        drop_pending_updates=True
    )

if __name__ == "__main__":
    asyncio.run(main())
