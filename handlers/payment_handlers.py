import asyncio
from aiogram import F, Router
from aiogram.types import CallbackQuery, Message, LabeledPrice, PreCheckoutQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from yookassa import Configuration, Payment

from config.settings import ADMIN_IDS
from config.payments import TARIFS, STARS_PRICES, PAYMENT_METHODS, YOOKASSA_SHOP_ID, YOOKASSA_SECRET_KEY
from database.models import add_payment, get_latest_subscription
from services.hiddify_service import HiddifyService

# Настройка ЮKassa
Configuration.account_id = YOOKASSA_SHOP_ID
Configuration.secret_key = YOOKASSA_SECRET_KEY

payment_router = Router()
hiddify_service = HiddifyService()

def extend_or_create_subscription(user_id: int, added_days: int):
    """Продлевает или создаёт подписку"""
    existing_uuid = get_latest_subscription(user_id)
    
    if existing_uuid:
        print(f"Продлеваем существующую подписку для {user_id}: uuid={existing_uuid}, +{added_days} дней")
        result = hiddify_service.create_or_extend_both(
            added_days=added_days, 
            user_id=user_id, 
            existing_uuid=existing_uuid
        )
    else:
        print(f"Новая подписка для {user_id}: {added_days} дней")
        result = hiddify_service.create_or_extend_both(
            added_days=added_days, 
            user_id=user_id
        )
    
    return result

@payment_router.callback_query(F.data.startswith("tarif_"))
async def tarif_chosen(callback: CallbackQuery, state: FSMContext):
    """Выбор тарифа"""
    tarif_name = callback.data.split("_", 1)[1]
    
    if tarif_name not in TARIFS:
        await callback.answer("Такой тариф не найден", show_alert=True)
        return
        
    days, rub_price = TARIFS[tarif_name]
    stars_price = STARS_PRICES.get(tarif_name, rub_price // 6)
    
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

@payment_router.callback_query(F.data.startswith("pay_stars_"))
async def pay_with_stars(callback: CallbackQuery, state: FSMContext):
    """Оплата звёздами Telegram"""
    data = await state.get_data()
    tarif_name = callback.data.split("_", 2)[2]
    days = data["days"]
    stars_amount = data["stars_price"]

    prices = [LabeledPrice(label=f"Подписка {tarif_name}", amount=stars_amount)]

    try:
        await callback.bot.send_invoice(
            chat_id=callback.message.chat.id,
            title=f"Magam VPN — {tarif_name}",
            description=f"Доступ к премиум VPN на {days} дней",
            payload=f"vpn_{callback.from_user.id}_{tarif_name}_{days}",
            provider_token="",  # для Stars оставляем пустым
            currency="XTR",
            prices=prices,
            need_name=False,
            need_phone_number=False,
            need_email=False,
            need_shipping_address=False,
            is_flexible=False,
            reply_markup=None
        )

        await callback.answer("Счёт выставлен! Оплатите ⭐ звёздами", show_alert=False)

    except Exception as e:
        print(f"Ошибка отправки Stars invoice: {e}")
        await callback.message.edit_text("❌ Не удалось создать счёт. Попробуйте позже или выберите другой способ.")

@payment_router.callback_query(F.data.startswith("pay_yookassa_"))
async def pay_yookassa(callback: CallbackQuery, state: FSMContext):
    """Оплата через ЮKassa"""
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
                        "vat_code": 1,
                        "payment_mode": "full_prepayment",
                        "payment_subject": "service"
                    }
                ]
            }
        })
       
        payment_url = payment.confirmation.confirmation_url
        payment_id = payment.id
        
        add_payment(
            callback.from_user.id,
            payment_id,
            tarif_name,
            days,
            str(payment.metadata)
        )
       
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💳 Оплатить сейчас", url=payment_url)],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="pay")]
        ])
       
        text = (
            f"Оплата через ЮKassa\n\n"
            f"Тариф: **{tarif_name}**\n"
            f"Сумма: **{amount} ₽**\n\n"
            "Нажмите кнопку ниже для перехода к оплате 👇"
        )
       
        await callback.message.edit_text(
            text,
            reply_markup=kb,
            parse_mode="Markdown"
        )
       
    except Exception as e:
        print(f"Ошибка создания платежа ЮKassa: {e}")
        await callback.message.edit_text("❌ Не удалось создать платёж. Попробуйте позже или напишите в поддержку.")
   
    await callback.answer()

@payment_router.pre_checkout_query()
async def pre_checkout_handler(pre_checkout_query: PreCheckoutQuery):
    """Обработчик предварительной проверки оплаты"""
    await pre_checkout_query.bot.answer_pre_checkout_query(
        pre_checkout_query_id=pre_checkout_query.id,
        ok=True
    )

@payment_router.message(F.successful_payment)
async def successful_stars_payment(message: Message):
    """Успешная оплата звёздами"""
    payment = message.successful_payment
    user_id = message.from_user.id
   
    try:
        _, uid_str, tarif_name, days_str = payment.invoice_payload.split("_")
        days = int(days_str)
    except:
        days = 7  # fallback
       
    result = extend_or_create_subscription(user_id, days)
   
    if result:
        await asyncio.sleep(8)  # даём Hiddify время
        text = (
            f"🎉 Оплата через ⭐ Stars прошла успешно!\n\n"
            f"Добавлено **+{days} дней** к подписке!\n"
            f"Сумма: {payment.total_amount} ⭐\n\n"
            f"Перейдите в «Установить VPN» → добавьте конфигурацию"
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📲 Главное меню", callback_data="back_main")]
        ])
        await message.answer(text, reply_markup=kb, parse_mode="Markdown")
    
        # Уведомляем админов
        admin_text = (
            f"⭐ НОВАЯ ОПЛАТА Stars!\n"
            f"Пользователь: {user_id} (@{message.from_user.username or 'нет'})\n"
            f"Тариф: {tarif_name} | {days} дней\n"
            f"Сумма: {payment.total_amount} ⭐"
        )
        
        for admin_id in ADMIN_IDS:
            try:
                await message.bot.send_message(admin_id, admin_text)
            except:
                pass
    else:
        await message.answer("❌ Ошибка при создании подписки. Обратитесь в поддержку.")