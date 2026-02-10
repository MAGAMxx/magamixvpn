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
    get_latest_subscription, add_review
)
from services.hiddify_service import HiddifyService

user_router = Router()
hiddify_service = HiddifyService()

class States(StatesGroup):
    waiting_free_check = State()
    waiting_review = State()

async def give_referral_bonus(referrer_id: int, referred_user_id: int, bot):
    """Выдаёт реферальный бонус"""
    existing_uuid = get_latest_subscription(referrer_id)
    added_days = REFERRAL_BONUS_DAYS
    
    # Получаем информацию о пользователях
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
        
        # Отправляем красочное уведомление в админскую группу в тему рефералов
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
                f"━━━━━━━━━━━━━━━━\n"
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
            
            # Fallback - отправляем админам в личку если группа недоступна
            fallback_text = f"Реферал от {referrer_id} → +{added_days} дней на обоих серверах для {referred_user_id}"
            for admin_id in ADMIN_IDS:
                try:
                    await bot.send_message(admin_id, fallback_text)
                except:
                    pass

def tarifs_menu():
    """Создаёт меню тарифов"""
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
    """Отправляет главное меню"""
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
    
    # Добавляем кнопку бесплатных дней если не брал
    if not user_got_free(user_id):
        kb.insert(1, [InlineKeyboardButton(text="🎁 Бесплатно 3 дня", callback_data="free_3days")])
    
    # Добавляем кнопку отзыва только если пользователь имел доступ к сервису
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
    """Обработчик команды /start"""
    user_id = message.from_user.id
    username = message.from_user.username or "нет"
    name = message.from_user.first_name

    # Проверяем реферальный параметр
    args = message.text.split()
    referrer_id = None
    if len(args) > 1 and args[1].startswith("ref_"):
        try:
            referrer_id = int(args[1].split("_")[1])
            if referrer_id == user_id:
                referrer_id = None
        except:
            referrer_id = None

    # Добавляем пользователя, если новый
    is_new = add_user_if_new(user_id, username)

    if is_new and referrer_id:
        await give_referral_bonus(referrer_id, user_id, message.bot)

    await send_main_menu(message, name, user_id)

@user_router.callback_query(F.data == "back_main")
async def back_main(callback: CallbackQuery):
    """Возврат в главное меню"""
    user_name = callback.from_user.first_name
    user_id = callback.from_user.id
    await send_main_menu(callback, user_name, user_id)
    await callback.answer()

@user_router.callback_query(F.data == "pay")
async def pay(callback: CallbackQuery):
    """Меню оплаты"""
    await callback.message.edit_text("💸 Выбери тариф:", reply_markup=tarifs_menu())
    await callback.answer()

@user_router.callback_query(F.data == "install")
async def install(callback: CallbackQuery):
    """Меню установки приложений"""
    user_id = callback.from_user.id
    
    # Получаем последнюю подписку пользователя
    selected_uuid = get_latest_subscription(user_id)
    
    if not selected_uuid:
        # Если нет подписки, показываем только ссылки на приложения
        text = (
            "📲 **Установка VPN**\n\n"
            "Сначала оплатите подписку, чтобы получить доступ к серверам.\n\n"
            "Выберите вашу операционную систему для скачивания приложения Happ:"
        )
        
        kb = []
        for os_name, link in HAPP_LINKS.items():
            kb.append([InlineKeyboardButton(text=f"📱 {os_name}", url=link)])
        
        kb.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")])
        
    else:
        # Если есть подписка, показываем ссылки на серверы
        from config.settings import DEEPLINK_BASE
        from config.servers import SERVERS_CONFIG
        
        # Определяем платформу (можно улучшить определение)
        platform = "Android"  # По умолчанию
        
        # Формируем ссылку на сервер
        deeplink_main = f"{DEEPLINK_BASE}{SERVERS_CONFIG['MAIN']['client_path']}/{selected_uuid}/"
        
        text = (
            "📲 **Установка VPN**\n\n"
            "✅ У вас есть активная подписка!\n"
            "Нажмите кнопки ниже для настройки:"
        )
        
        kb = [
            [InlineKeyboardButton(text="🔗 Скачать Happ", url=HAPP_LINKS.get(platform, HAPP_LINKS["Android"]))],
            [InlineKeyboardButton(text="🇷🇺 Добавить конфигурацию", url=deeplink_main)],
            [InlineKeyboardButton(text="�  Главное меню", callback_data="back_main")]
        ]
    
    await callback.message.edit_text(
        text, 
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb),
        parse_mode="Markdown"
    )
    await callback.answer()

@user_router.callback_query(F.data == "referral")
async def referral(callback: CallbackQuery):
    """Реферальная система"""
    user_id = callback.from_user.id
    ref_link = f"https://t.me/magamixvpn_bot?start=ref_{user_id}"
    
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
    """Бесплатные 3 дня"""
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
    
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    await state.set_state(States.waiting_free_check)
    await callback.answer()

@user_router.callback_query(F.data == "check_subscription")
async def check_subscription(callback: CallbackQuery, state: FSMContext):
    """Проверка подписки на канал"""
    user_id = callback.from_user.id
    
    try:
        # Проверяем подписку на канал
        member = await callback.bot.get_chat_member("@MAGAMIX_VPN", user_id)
        if member.status in ["member", "administrator", "creator"]:
            # Выдаём бесплатные дни
            result = hiddify_service.create_or_extend_both(added_days=3, user_id=user_id)
            
            if result:
                mark_got_free(user_id)
                
                await asyncio.sleep(8)  # даём Hiddify время
                
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
    """Оставить отзыв"""
    user_id = callback.from_user.id
    
    # Проверяем, может ли пользователь оставить отзыв
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
    """Обработка отзыва"""
    user_id = message.from_user.id
    username = message.from_user.username or "none"
    first_name = message.from_user.first_name or "Неизвестно"
    review_text = message.text
    
    # Добавляем отзыв в БД и получаем его номер
    review_id = add_review(user_id, username, review_text)
    
    await message.answer(
        "✅ **Спасибо за отзыв!**\n\n"
        "Ваш отзыв отправлен на модерацию и скоро появится в нашем канале! 💙",
        parse_mode="Markdown"
    )
    
    await state.clear()
    
    # Отправляем отзыв в админскую группу в тему отзывов с кнопками модерации
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
    
    # Кнопки модерации
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
        
        # Fallback - отправляем админам в личку
        for admin_id in ADMIN_IDS:
            try:
                await message.bot.send_message(admin_id, admin_text, parse_mode="Markdown", reply_markup=kb)
            except:
                pass