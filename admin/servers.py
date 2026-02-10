"""
Модуль управления серверами
"""
import requests
from aiogram import F, Router
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from config.settings import ADMIN_IDS

servers_router = Router()

# Фильтр только для админов
servers_router.callback_query.filter(lambda callback: callback.from_user.id in ADMIN_IDS)

@servers_router.callback_query(F.data == "admin_servers")
async def admin_servers(callback: CallbackQuery):
    """Управление серверами"""
    text = (
        "🔧 **Управление серверами**\n\n"
        "Выберите действие:"
    )
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Статус серверов", callback_data="admin_server_status")],
        [InlineKeyboardButton(text="🔄 Проверить подключение", callback_data="admin_check_servers")],
        [InlineKeyboardButton(text="📈 Нагрузка серверов", callback_data="admin_server_load")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")]
    ])
    
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()

@servers_router.callback_query(F.data == "admin_server_status")
async def admin_server_status(callback: CallbackQuery):
    """Статус серверов"""
    from config.servers import SERVERS_CONFIG
    
    status_text = "📊 **Статус серверов:**\n\n"
    
    for server_key, server_info in SERVERS_CONFIG.items():
        try:
            # Простая проверка доступности
            response = requests.get(f"{server_info['admin_path']}/api/v2/admin/user/", 
                                  headers={"Hiddify-API-Key": server_info["api_key"]}, 
                                  timeout=5)
            if response.status_code == 200:
                status = "🟢 Онлайн"
            else:
                status = f"🟡 Проблемы ({response.status_code})"
        except:
            status = "🔴 Офлайн"
        
        status_text += f"{server_info['name']}: {status}\n"
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Обновить", callback_data="admin_server_status")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_servers")]
    ])
    
    await callback.message.edit_text(status_text, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()