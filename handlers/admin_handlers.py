import os
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from config.settings import ADMIN_IDS, ADMIN_GROUP_ID, PUBLIC_REVIEWS_CHANNEL
from database.models import get_review_by_id
from admin.main import admin_router
from admin.stats import stats_router
from admin.users import users_router
from admin.broadcast import broadcast_router
from admin.servers import servers_router
from admin.promo import promo_router

# Главный роутер для админки
main_admin_router = Router()

# Подключаем все админские роутеры
main_admin_router.include_router(admin_router)
main_admin_router.include_router(stats_router)
main_admin_router.include_router(users_router)
main_admin_router.include_router(broadcast_router)
main_admin_router.include_router(servers_router)
main_admin_router.include_router(promo_router)

# Фильтр только для админов
main_admin_router.message.filter(lambda message: message.from_user.id in ADMIN_IDS)
main_admin_router.callback_query.filter(lambda callback: callback.from_user.id in ADMIN_IDS)

@main_admin_router.message(Command("backup"))
async def backup_database(message: Message):
    """Создание бэкапа базы данных"""
    import shutil
    from datetime import datetime
    
    try:
        backup_name = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        backup_path = f"database/data/{backup_name}"
        
        shutil.copy2("database/data/users.db", backup_path)
        
        await message.answer(
            f"✅ **Бэкап создан**\n\n"
            f"Файл: `{backup_name}`\n"
            f"Размер: {os.path.getsize(backup_path)} байт",
            parse_mode="Markdown"
        )
        
        # Отправляем файл админу
        with open(backup_path, 'rb') as backup_file:
            await message.answer_document(
                backup_file,
                caption="📁 Бэкап базы данных"
            )
            
    except Exception as e:
        await message.answer(f"❌ Ошибка создания бэкапа: {e}")

# Обработчики модерации отзывов
@main_admin_router.callback_query(lambda c: c.data.startswith("approve_review_"))
async def approve_review(callback: CallbackQuery):
    """Одобрить отзыв и опубликовать в канале"""
    try:
        review_id = int(callback.data.split("_")[-1])
        review_data = get_review_by_id(review_id)
        
        if not review_data:
            await callback.answer("❌ Отзыв не найден", show_alert=True)
            return
        
        # review_data: (id, user_id, username, review_text, created_at)
        user_id, username, review_text, created_at = review_data[1], review_data[2], review_data[3], review_data[4]
        
        # Публикуем отзыв в канале
        published_text = (
            f"⭐ **ОТЗЫВ КЛИЕНТА**\n\n"
            f"💬 «{review_text}»\n\n"
            f"👤 **От:** @{username}\n"
            f"📅 **{created_at}**\n\n"
            f"🔥 **Присоединяйтесь к нам:** @MAGAMIX_VPN"
        )
        
        await callback.bot.send_message(
            chat_id=PUBLIC_REVIEWS_CHANNEL,
            text=published_text,
            parse_mode="Markdown"
        )
        
        # Обновляем сообщение в админской группе
        await callback.message.edit_text(
            f"✅ **ОТЗЫВ №{review_id} ОДОБРЕН И ОПУБЛИКОВАН**\n\n"
            f"👤 **Пользователь:** `{user_id}` (@{username})\n"
            f"💬 **Текст:** «{review_text}»\n"
            f"📅 **Опубликован:** {created_at}\n\n"
            f"✨ **Модератор:** @{callback.from_user.username or callback.from_user.first_name}",
            parse_mode="Markdown"
        )
        
        await callback.answer("✅ Отзыв одобрен и опубликован!", show_alert=True)
        
    except Exception as e:
        print(f"Ошибка одобрения отзыва: {e}")
        await callback.answer("❌ Ошибка при одобрении отзыва", show_alert=True)

@main_admin_router.callback_query(lambda c: c.data.startswith("contact_review_"))
async def contact_review(callback: CallbackQuery):
    """Связаться с автором отзыва"""
    try:
        review_id = int(callback.data.split("_")[-1])
        review_data = get_review_by_id(review_id)
        
        if not review_data:
            await callback.answer("❌ Отзыв не найден", show_alert=True)
            return
        
        user_id, username, review_text, created_at = review_data[1], review_data[2], review_data[3], review_data[4]
        
        # Обновляем сообщение в админской группе
        await callback.message.edit_text(
            f"💬 **СВЯЗЬ С АВТОРОМ ОТЗЫВА №{review_id}**\n\n"
            f"👤 **Пользователь:** `{user_id}` (@{username})\n"
            f"💬 **Текст отзыва:** «{review_text}»\n"
            f"📅 **Дата:** {created_at}\n\n"
            f"📞 **Статус:** Требуется связь с клиентом\n"
            f"🔍 **Модератор:** @{callback.from_user.username or callback.from_user.first_name}\n\n"
            f"💡 **Действие:** Свяжитесь с пользователем для выяснения причин негативного отзыва",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✅ Проблема решена", callback_data=f"resolved_review_{review_id}")]
            ])
        )
        
        await callback.answer("📞 Отмечено для связи с клиентом", show_alert=True)
        
    except Exception as e:
        print(f"Ошибка обработки связи с отзывом: {e}")
        await callback.answer("❌ Ошибка при обработке", show_alert=True)

@main_admin_router.callback_query(lambda c: c.data.startswith("reject_review_"))
async def reject_review(callback: CallbackQuery):
    """Отклонить отзыв"""
    try:
        review_id = int(callback.data.split("_")[-1])
        review_data = get_review_by_id(review_id)
        
        if not review_data:
            await callback.answer("❌ Отзыв не найден", show_alert=True)
            return
        
        user_id, username, review_text, created_at = review_data[1], review_data[2], review_data[3], review_data[4]
        
        # Обновляем сообщение в админской группе
        await callback.message.edit_text(
            f"❌ **ОТЗЫВ №{review_id} ОТКЛОНЁН**\n\n"
            f"👤 **Пользователь:** `{user_id}` (@{username})\n"
            f"💬 **Текст:** «{review_text}»\n"
            f"📅 **Дата:** {created_at}\n\n"
            f"🚫 **Причина:** Неподходящий контент / спам\n"
            f"👨‍💼 **Модератор:** @{callback.from_user.username or callback.from_user.first_name}",
            parse_mode="Markdown"
        )
        
        await callback.answer("❌ Отзыв отклонён", show_alert=True)
        
    except Exception as e:
        print(f"Ошибка отклонения отзыва: {e}")
        await callback.answer("❌ Ошибка при отклонении отзыва", show_alert=True)

@main_admin_router.callback_query(lambda c: c.data.startswith("resolved_review_"))
async def resolved_review(callback: CallbackQuery):
    """Отметить проблему как решённую"""
    try:
        review_id = int(callback.data.split("_")[-1])
        
        # Обновляем сообщение
        current_text = callback.message.text
        updated_text = current_text.replace(
            "📞 **Статус:** Требуется связь с клиентом",
            "✅ **Статус:** Проблема решена"
        ).replace(
            "💡 **Действие:** Свяжитесь с пользователем для выяснения причин негативного отзыва",
            f"🎯 **Результат:** Проблема успешно решена модератором @{callback.from_user.username or callback.from_user.first_name}"
        )
        
        await callback.message.edit_text(
            updated_text,
            parse_mode="Markdown"
        )
        
        await callback.answer("✅ Проблема отмечена как решённая!", show_alert=True)
        
    except Exception as e:
        print(f"Ошибка отметки решения: {e}")
        await callback.answer("❌ Ошибка при обновлении статуса", show_alert=True)

# Экспортируем главный роутер
admin_router = main_admin_router