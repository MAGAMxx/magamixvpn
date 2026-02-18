import asyncio
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config.settings import CHANNEL_LINK, FREE_TRIAL_DAYS, REFERRAL_BONUS_DAYS, ADMIN_GROUP_ID, REFERRAL_TOPIC_ID, REVIEWS_TOPIC_ID, PUBLIC_REVIEWS_CHANNEL, ADMIN_IDS
from config.apps import HAPP_LINKS
from config.payments import TARIFS
from database.models import (
    add_user_if_new, user_got_free, mark_got_free, 
    get_latest_subscription, add_review,
    set_user_promo_discount, get_user_active_discount
)
from services.hiddify_service import HiddifyService

user_router = Router()
hiddify_service = HiddifyService()

class States(StatesGroup):
    waiting_free_check = State()
    waiting_review = State()
    waiting_promo_code = State()

async def give_referral_bonus(referrer_id: int, referred_user_id: int, bot):
    existing_uuid = get_latest_subscription(referrer_id)
    added_days = REFERRAL_BONUS_DAYS
    
    try:
        referrer_info = await bot.get_chat(referrer_id)
        referred_info = await bot.get_chat(referred_user_id)
        
        referrer_name = referrer_info.first_name or "Неизвестно"
        referrer_username = referrer_info.username or "нет"
        
        referred_name = referred_info.first_name or "Неизвестно"
        referred_username = referred_info.username or "нет"
    except:
        referrer_name = "Неизвестно"
        referrer_username = "нет"
        referred_name = "Неизвестно" 
        referred_username = "нет"
    
    if existing_uuid:
        result = hiddify_service.create_or_extend_both(
            added_days=added_days, 
            user_id=referrer_id, 
            existing_uuid=existing_uuid
        )
    else:
        result = hiddify_service.create_or_extend_both(
            added_days=added_days, 
            user_id=referrer_id
        )
    
    if result:
        await bot.send_message(
            referrer_id,
            f"🎉 Новый друг по твоей ссылке! +{added_days} дня к подписке добавлено!"
        )
        
        from datetime import datetime
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        try:
            admin_text = (
                f"🎯 **НОВЫЙ РЕФЕРАЛ**\n\n"
                f"👤 **Реферер (получил бонус):**\n"
                f"┣ **Имя:** {referrer_name}\n"
                f"┣ **ID:** `{referrer_id}`\n"
                f"┗ **Username:** @{referrer_username}\n\n"
                f"🆕 **Новый пользователь:**\n"
                f"┣ **Имя:** {referred_name}\n"
                f"┣ **ID:** `{referred_user_id}`\n"
                f"┗ **Username:** @{referred_username}\n\n"
                f"🎁 **Реферальный бонус:**\n"
                f"┣ **Дни:** +{added_days} дней\n"
                f"┣ **Серверы:** RU + NL (оба)\n"
                f"┗ **Статус:** ✅ Успешно начислен\n\n"
                f"🕒 **Время:** `{current_time}`\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"💰 **Реферальная программа работает!**"
            )
            
            await bot.send_message(
                chat_id=ADMIN_GROUP_ID,
                text=admin_text,
                parse_mode="Markdown",
                message_thread_id=REFERRAL_TOPIC_ID
            )
        except Exception as e:
            print(f"Ошибка отправки уведомления о реферале в группу: {e}")
            
            fallback_text = f"Реферал от {referrer_id} → +{added_days} дней на обоих серверах для {referred_user_id}"
            for admin_id in ADMIN_IDS:
                try:
                    await bot.send_message(admin_id, fallback_text)
                except:
                    pass

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
        [InlineKeyboardButton(text="📝 Отзывы", url="https://t.me/otziv_magamvpn")],
        [InlineKeyboardButton(text="🆘 Поддержка", url="t.me/magamix_support")]
    ]
    
    if not user_got_free(user_id):
        kb.insert(1, [InlineKeyboardButton(text="🎁 Бесплатно 3 дня", callback_data="free_3days")])
    
    has_subscription = get_latest_subscription(user_id) is not None
    used_free_trial = user_got_free(user_id)
    
    if has_subscription or used_free_trial:
        kb.insert(-2, [InlineKeyboardButton(text="📝 Оставить отзыв", callback_data="leave_review")])

    markup = InlineKeyboardMarkup(inline_keyboard=kb)

    if isinstance(event, Message):
        await event.answer(text, reply_markup=markup)
    else:
        await event.message.edit_text(text, reply_markup=markup)

@user_router.message(Command("start"))
async def start(message: Message):
    user_id = message.from_user.id
    username = message.from_user.username or "нет"
    name = message.from_user.first_name

    args = message.text.split()
    referrer_id = None
    if len(args) > 1 and args[1].startswith("ref_"):
        try:
            referrer_id = int(args[1].split("_")[1])
            if referrer_id == user_id:
                referrer_id = None
        except:
            referrer_id = None

    is_new = add_user_if_new(user_id, username)

    if is_new and referrer_id:
        await give_referral_bonus(referrer_id, user_id, message.bot)

    await send_main_menu(message, name, user_id)

@user_router.callback_query(F.data == "back_main")
async def back_main(callback: CallbackQuery):
    user_name = callback.from_user.first_name
    user_id = callback.from_user.id
    await send_main_menu(callback, user_name, user_id)
    await callback.answer()

@user_router.callback_query(F.data == "pay")
async def pay(callback: CallbackQuery):
    await callback.message.edit_text("💸 Выбери тариф:", reply_markup=tarifs_menu())
    await callback.answer()

@user_router.message(Command("promo"))
async def promo_command(message: Message, state: FSMContext):
    user_id = message.from_user.id
    
    active_discount = get_user_active_discount(user_id)
    if active_discount:
        promo_code, discount = active_discount
        await message.answer(
            f"🎫 У вас уже активирован промокод **{promo_code}** со скидкой **{discount}%**\n\n"
            f"Скидка применится автоматически при следующей покупке.",
            parse_mode="Markdown"
        )
        return
    
    await message.answer(
        "🎫 **Введите промокод**\n\n"
        "Напишите ваш промокод, и если он действителен, вы получите скидку на следующую покупку!",
        parse_mode="Markdown"
    )
    await state.set_state(States.waiting_promo_code)

@user_router.message(States.waiting_promo_code)
async def process_promo_code(message: Message, state: FSMContext):
    user_id = message.from_user.id
    entered_code = message.text.strip().upper()
    
    from admin.promo import get_active_promo_codes
    promo_codes = get_active_promo_codes()
    
    if entered_code not in promo_codes:
        await message.answer(
            "❌ **Промокод не найден**\n\n"
            "Проверьте правильность ввода и попробуйте ещё раз.\n"
            "Для отмены отправьте /start",
            parse_mode="Markdown"
        )
        return
    
    discount = promo_codes[entered_code]
    
    set_user_promo_discount(user_id, entered_code, discount)
    
    import sqlite3
    conn = sqlite3.connect("database/data/users.db")
    c = conn.cursor()
    c.execute("INSERT INTO promo_usage (promo_code, user_id, discount_amount) VALUES (?, ?, ?)",
              (entered_code, user_id, discount))
    conn.commit()
    conn.close()
    
    await message.answer(
        f"✅ **Промокод активирован!**\n\n"
        f"🎫 Промокод: **{entered_code}**\n"
        f"💰 Скидка: **{discount}%**\n\n"
        f"Скидка будет применена к вашей следующей покупке автоматически.\n"
        f"Скидка действует на **1 покупку**.",
        parse_mode="Markdown"
    )
    await state.clear()

async def show_device_selection(callback: CallbackQuery):
    text = "📱 **Выберите ваше устройство:**"
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🤖 Android", callback_data="install_android")],
        [InlineKeyboardButton(text="🍎 iOS", callback_data="install_ios")],
        [InlineKeyboardButton(text="🖥 Windows", callback_data="install_windows")],
        [InlineKeyboardButton(text="🍏 macOS", callback_data="install_macos")],
        [InlineKeyboardButton(text="🐧 Linux", callback_data="install_linux")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")]
    ])
    
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")

@user_router.callback_query(F.data == "install")
async def install(callback: CallbackQuery):
    await show_device_selection(callback)
    await callback.answer()

@user_router.callback_query(F.data.startswith("install_"))
async def install_device(callback: CallbackQuery):
    device = callback.data.replace("install_", "")
    user_id = callback.from_user.id
    
    device_info = {
        "android": {"name": "Android", "icon": "🤖"},
        "ios": {"name": "iOS", "icon": "🍎"},
        "windows": {"name": "Windows", "icon": "🖥"},
        "macos": {"name": "macOS", "icon": "🍏"},
        "linux": {"name": "Linux", "icon": "🐧"}
    }
    
    device_name = device_info.get(device, {}).get("name", device.capitalize())
    device_icon = device_info.get(device, {}).get("icon", "📱")
    
    selected_uuid = get_latest_subscription(user_id)
    
    if not selected_uuid:
        text = (
            f"{device_icon} **Установка VPN для {device_name}**\n\n"
            "❌ **У вас нет активной подписки!**\n\n"
            "Сначала оплатите подписку, чтобы получить доступ к серверам."
        )
        
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💳 Оплатить VPN", callback_data="pay")],
            [InlineKeyboardButton(text="🎁 Бесплатно 3 дня", callback_data="free_3days")],
            [InlineKeyboardButton(text="🔙 Главное меню", callback_data="back_main")]
        ])
        
    else:
        from config.settings import DEEPLINK_BASE
        from config.servers import SERVERS_CONFIG
        
        deeplink_ru = f"{DEEPLINK_BASE}{SERVERS_CONFIG['RU']['client_path']}/{selected_uuid}/"
        deeplink_nl = f"{DEEPLINK_BASE}{SERVERS_CONFIG['NL']['client_path']}/{selected_uuid}/"
        
        device_map = {
            "android": "Android",
            "ios": "iOS",
            "windows": "Windows",
            "macos": "macOS",
            "linux": "Linux"
        }
        
        happ_device = device_map.get(device, "Android")
        happ_link = HAPP_LINKS.get(happ_device, HAPP_LINKS.get("Android"))
        
        text = (
            f"{device_icon} **Установка VPN для {device_name}**\n\n"
            "✅ **У вас есть активная подписка!**\n\n"
            "📋 **Быстрая инструкция:**\n"
            "1. Скачайте и установите Happ\n"
            "2. Добавьте подписки для обоих серверов\n"
            "3. Разрешите открытие ссылок в Happ\n"
            "4. Нажмите «Подключить» в приложении"
        )
        
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"⬇️ Скачать Happ", url=happ_link)],
            [InlineKeyboardButton(text="Добавить подписку🇷🇺", url=deeplink_ru)],
            [InlineKeyboardButton(text="Добавить подписку🇳🇱", url=deeplink_nl)],
            [InlineKeyboardButton(text="📱 Выбрать другое устройство", callback_data="install")],
            [InlineKeyboardButton(text="🔙 Главное меню", callback_data="back_main")]
        ])
    
    await callback.message.edit_text(
        text, 
        reply_markup=kb,
        parse_mode="Markdown"
    )
    await callback.answer()


@user_router.callback_query(F.data == "referral")
async def referral(callback: CallbackQuery):
    user_id = callback.from_user.id
    ref_link = f"https://t.me/magam_vpn_bot?start=ref_{user_id}"
    
    text = (
        "👥 **Пригласи друзей и получи бонусы!**\n\n"
        "🎁 За каждого друга ты получишь **3 дня** VPN\n"
        "🎁 Твой друг тоже получит **3 дня** бесплатно\n\n"
        f"Твоя реферальная ссылка:\n`{ref_link}`\n\n"
        "Просто отправь эту ссылку друзьям!"
    )
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📤 Поделиться", url=f"https://t.me/share/url?url={ref_link}")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")]
    ])
    
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()

@user_router.callback_query(F.data == "free_3days")
async def free_3days(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    
    if user_got_free(user_id):
        await callback.answer("Вы уже получали бесплатные дни!", show_alert=True)
        return
    
    text = (
        f"🎁 **Бесплатные 3 дня VPN!**\n\n"
        f"Для получения бесплатного доступа:\n"
        f"1️⃣ Подпишись на канал: {CHANNEL_LINK}\n"
        f"2️⃣ Нажми кнопку «Проверить подписку»\n\n"
        f"После проверки ты получишь 3 дня бесплатного VPN! 🚀"
    )
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Подписаться", url=CHANNEL_LINK)],
        [InlineKeyboardButton(text="✅ Проверить подписку", callback_data="check_subscription")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")]
    ])
    
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await state.set_state(States.waiting_free_check)
    await callback.answer()

@user_router.callback_query(F.data == "check_subscription")
async def check_subscription(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    
    try:
        member = await callback.bot.get_chat_member("@MAGAMIX_VPN", user_id)
        if member.status in ["member", "administrator", "creator"]:
            result = hiddify_service.create_or_extend_both(added_days=3, user_id=user_id)
            
            if result:
                mark_got_free(user_id)
                
                await asyncio.sleep(8)
                
                text = (
                    "🎉 **Поздравляем!**\n\n"
                    "✅ Подписка проверена\n"
                    "🎁 **3 дня VPN** добавлено к вашему аккаунту!\n\n"
                    "Перейдите в «Установить VPN» → добавьте конфигурацию"
                )
                
                kb = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="📲 Установить VPN", callback_data="install")],
                    [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_main")]
                ])
                
                await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
            else:
                await callback.message.edit_text("❌ Ошибка при создании подписки. Попробуйте позже.")
        else:
            await callback.answer("❌ Вы не подписаны на канал!", show_alert=True)
            
    except Exception as e:
        print(f"Ошибка проверки подписки: {e}")
        await callback.answer("❌ Ошибка проверки. Попробуйте позже.", show_alert=True)
    
    await state.clear()

@user_router.callback_query(F.data == "leave_review")
async def leave_review(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    
    has_subscription = get_latest_subscription(user_id) is not None
    used_free_trial = user_got_free(user_id)
    
    if not has_subscription and not used_free_trial:
        await callback.answer(
            "❌ Чтобы оставить отзыв, нужно сначала воспользоваться нашим сервисом!\n"
            "Получите бесплатные 3 дня или оплатите подписку.",
            show_alert=True
        )
        return
    
    text = (
        "📝 **Оставить отзыв**\n\n"
        "Напишите ваш отзыв о нашем VPN сервисе.\n"
        "Ваше мнение очень важно для нас! 💙"
    )
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")]
    ])
    
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    await state.set_state(States.waiting_review)
    await callback.answer()

@user_router.message(States.waiting_review)
async def process_review(message: Message, state: FSMContext):
    user_id = message.from_user.id
    username = message.from_user.username or "none"
    first_name = message.from_user.first_name or "Неизвестно"
    review_text = message.text
    
    review_id = add_review(user_id, username, review_text)
    
    await message.answer(
        "✅ **Спасибо за отзыв!**\n\n"
        "Ваш отзыв отправлен на модерацию и скоро появится в нашем канале! 💙",
        parse_mode="Markdown"
    )
    
    await state.clear()
    
    from datetime import datetime
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    admin_text = (
        f"📝 **НОВЫЙ ОТЗЫВ №{review_id}**\n\n"
        f"👤 **Пользователь:**\n"
        f"┣ **Имя:** {first_name}\n"
        f"┣ **ID:** `{user_id}`\n"
        f"┗ **Username:** @{username}\n\n"
        f"💬 **Текст отзыва:**\n"
        f"«{review_text}»\n\n"
        f"🕒 **Время:** `{current_time}`"
    )
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Одобрить", callback_data=f"approve_review_{review_id}"),
            InlineKeyboardButton(text="💬 Связаться", callback_data=f"contact_review_{review_id}")
        ],
        [InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_review_{review_id}")]
    ])
    
    try:
        await message.bot.send_message(
            chat_id=ADMIN_GROUP_ID,
            text=admin_text,
            parse_mode="Markdown",
            reply_markup=kb,
            message_thread_id=REVIEWS_TOPIC_ID
        )
    except Exception as e:
        print(f"Ошибка отправки отзыва в админскую группу: {e}")
        
        for admin_id in ADMIN_IDS:
            try:
                await message.bot.send_message(admin_id, admin_text, parse_mode="Markdown", reply_markup=kb)
            except:
                pass
