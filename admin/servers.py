import requests
from aiogram import F, Router
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from config.settings import ADMIN_IDS

servers_router = Router()

servers_router.callback_query.filter(lambda callback: callback.from_user.id in ADMIN_IDS)

@servers_router.callback_query(F.data == "admin_servers")
async def admin_servers(callback: CallbackQuery):
    text = (
        "🔧 **СЕРВЕРЫ**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Управление VPN серверами:"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Статус серверов", callback_data="admin_server_status")],
        [InlineKeyboardButton(text="📈 Нагрузка серверов", callback_data="admin_server_load")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")]
    ])

    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()

@servers_router.callback_query(F.data == "admin_server_status")
async def admin_server_status(callback: CallbackQuery):
    from config.servers import SERVERS_CONFIG

    text = "📊 **СТАТУС СЕРВЕРОВ**\n━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"

    online = 0
    for server_key, server_info in SERVERS_CONFIG.items():
        try:
            import time
            start = time.time()
            response = requests.get(
                f"{server_info['admin_path']}/api/v2/admin/user/",
                headers={"Hiddify-API-Key": server_info["api_key"]},
                timeout=5
            )
            latency = int((time.time() - start) * 1000)

            if response.status_code == 200:
                data = response.json()
                user_count = len(data) if isinstance(data, list) else "N/A"
                status = f"🟢 Онлайн ({latency}ms)"
                online += 1
                text += f"**{server_key}** {server_info['name']}\n"
                text += f"┣ Статус: {status}\n"
                text += f"┗ Пользователей: {user_count}\n\n"
            else:
                text += f"**{server_key}** {server_info['name']}\n"
                text += f"┗ 🟡 Код: {response.status_code}\n\n"
        except requests.exceptions.Timeout:
            text += f"**{server_key}** {server_info['name']}\n"
            text += f"┗ 🔴 Таймаут\n\n"
        except Exception as e:
            text += f"**{server_key}** {server_info['name']}\n"
            text += f"┗ 🔴 Ошибка: {str(e)[:40]}\n\n"

    text += f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    text += f"📊 Итого: **{online}/{len(SERVERS_CONFIG)}** онлайн"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Обновить", callback_data="admin_server_status")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_servers")]
    ])

    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()

@servers_router.callback_query(F.data == "admin_server_load")
async def admin_server_load(callback: CallbackQuery):
    from config.servers import SERVERS_CONFIG

    await callback.answer("📈 Получаю данные...")

    text = "📈 **НАГРУЗКА СЕРВЕРОВ**\n━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"

    for server_key, server_info in SERVERS_CONFIG.items():
        try:
            response = requests.get(
                f"{server_info['admin_path']}/api/v2/admin/user/",
                headers={"Hiddify-API-Key": server_info["api_key"]},
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    total_users = len(data)
                    active_users = sum(1 for user in data if user.get('package_days', 0) > 0)

                    if total_users < 100:
                        load_bar = "🟩🟩🟩🟩🟩 Низкая"
                    elif total_users < 300:
                        load_bar = "🟨🟨🟨⬜⬜ Средняя"
                    else:
                        load_bar = "🟥🟥🟥🟥🟥 Высокая"

                    text += f"🖥 **{server_key}** {server_info['name']}\n"
                    text += f"┣ Всего: **{total_users}**\n"
                    text += f"┣ Активных: **{active_users}**\n"
                    text += f"┗ Нагрузка: {load_bar}\n\n"
                else:
                    text += f"⚠️ **{server_key}**: Неожиданный ответ\n\n"
            else:
                text += f"❌ **{server_key}**: Ошибка {response.status_code}\n\n"

        except Exception as e:
            text += f"❌ **{server_key}**: {str(e)[:40]}\n\n"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Обновить", callback_data="admin_server_load")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_servers")]
    ])

    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")

@servers_router.callback_query(F.data == "admin_check_servers")
async def admin_check_servers(callback: CallbackQuery):
    await callback.answer()
    from admin.servers import admin_server_status
    await admin_server_status(callback)
