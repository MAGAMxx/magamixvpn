"""
Главный модуль админ панели - улучшенная версия
"""
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from config.settings import ADMIN_IDS

admin_router = Router()

# Фильтр только для админов
admin_router.message.filter(lambda message: message.from_user.id in ADMIN_IDS)
admin_router.callback_query.filter(lambda callback: callback.from_user.id in ADMIN_IDS)

@admin_router.message(Command("admin"))
async def admin_panel(message: Message):
    """Главная админ панель - красивая версия"""
    text = (
        "🔧 **АДМИН ПАНЕЛЬ MAGAM VPN**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "👋 Добро пожаловать в панель управления!\n"
        "Выберите нужный раздел:"
    )
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats"),
            InlineKeyboardButton(text="💰 Финансы", callback_data="admin_finance")
        ],
        [
            InlineKeyboardButton(text="👥 Пользователи", callback_data="admin_users"),
            InlineKeyboardButton(text="🎫 Промокоды", callback_data="admin_promo")
        ],
        [
            InlineKeyboardButton(text="📤 Рассылка", callback_data="admin_broadcast"),
            InlineKeyboardButton(text="🔧 Серверы", callback_data="admin_servers")
        ],
        [
            InlineKeyboardButton(text="⚙️ Системные команды", callback_data="admin_system"),
            InlineKeyboardButton(text="📋 Быстрые действия", callback_data="admin_quick")
        ]
    ])
    
    await message.answer(text, reply_markup=kb, parse_mode="Markdown")

@admin_router.callback_query(F.data == "admin_system")
async def admin_system(callback: CallbackQuery):
    """Системные команды"""
    text = (
        "⚙️ **СИСТЕМНЫЕ КОМАНДЫ**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "🛠️ Управление системой и обслуживание:"
    )
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💾 Создать бэкап", callback_data="system_backup"),
            InlineKeyboardButton(text="📋 Показать логи", callback_data="system_logs")
        ],
        [
            InlineKeyboardButton(text="🔄 Перезапуск бота", callback_data="system_restart"),
            InlineKeyboardButton(text="📊 Системная информация", callback_data="system_info")
        ],
        [
            InlineKeyboardButton(text="🧹 Очистка кэша", callback_data="system_cache"),
            InlineKeyboardButton(text="🔍 Проверка БД", callback_data="system_db_check")
        ],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")]
    ])
    
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()

@admin_router.callback_query(F.data == "admin_quick")
async def admin_quick(callback: CallbackQuery):
    """Быстрые действия"""
    text = (
        "📋 **БЫСТРЫЕ ДЕЙСТВИЯ**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "⚡ Часто используемые команды:"
    )
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📊 Быстрая статистика", callback_data="quick_stats"),
            InlineKeyboardButton(text="👥 Последние пользователи", callback_data="quick_users")
        ],
        [
            InlineKeyboardButton(text="💳 Последние платежи", callback_data="quick_payments"),
            InlineKeyboardButton(text="🎫 Активные промокоды", callback_data="quick_promos")
        ],
        [
            InlineKeyboardButton(text="🔥 Популярные серверы", callback_data="quick_servers"),
            InlineKeyboardButton(text="⚠️ Проблемы системы", callback_data="quick_issues")
        ],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")]
    ])
    
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()

@admin_router.callback_query(F.data == "quick_stats")
async def quick_stats(callback: CallbackQuery):
    """Быстрая статистика"""
    import sqlite3
    from datetime import datetime
    
    conn = sqlite3.connect("database/data/users.db")
    c = conn.cursor()
    
    # Основные метрики
    c.execute("SELECT COUNT(*) FROM users")
    total_users = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM subscriptions WHERE status = 'active'")
    active_subs = c.fetchone()[0]
    
    today = datetime.now().strftime("%Y-%m-%d")
    c.execute("SELECT COUNT(*) FROM users WHERE reg_date LIKE ?", (f"{today}%",))
    today_users = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM payments WHERE status = 'completed'")
    completed_payments = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM payments WHERE status = 'pending'")
    pending_payments = c.fetchone()[0]
    
    conn.close()
    
    # Вычисляем процент активности
    activity_percent = (active_subs / max(total_users, 1)) * 100
    
    text = (
        f"⚡ **БЫСТРАЯ СТАТИСТИКА**\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👥 **Пользователи:**\n"
        f"• Всего: **{total_users}**\n"
        f"• Активных подписок: **{active_subs}** ({activity_percent:.1f}%)\n"
        f"• Новых сегодня: **{today_users}**\n\n"
        f"💳 **Платежи:**\n"
        f"• Завершенных: **{completed_payments}**\n"
        f"• Ожидающих: **{pending_payments}**\n\n"
        f"📊 **Активность:** {'🔥 Высокая' if activity_percent > 50 else '📈 Средняя' if activity_percent > 20 else '📉 Низкая'}"
    )
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📊 Полная статистика", callback_data="admin_stats"),
            InlineKeyboardButton(text="🔄 Обновить", callback_data="quick_stats")
        ],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_quick")]
    ])
    
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()

@admin_router.callback_query(F.data == "quick_promos")
async def quick_promos(callback: CallbackQuery):
    """Быстрый обзор промокодов"""
    from config.payments import PROMO_CODES
    import sqlite3
    
    if not PROMO_CODES:
        text = "🎫 **ПРОМОКОДЫ**\n━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n❌ Активных промокодов нет"
    else:
        conn = sqlite3.connect("database/data/users.db")
        c = conn.cursor()
        
        text = f"🎫 **АКТИВНЫЕ ПРОМОКОДЫ** ({len(PROMO_CODES)})\n━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        
        # Показываем первые 5 промокодов с статистикой
        for i, (code, discount) in enumerate(list(PROMO_CODES.items())[:5], 1):
            c.execute("SELECT COUNT(*) FROM promo_usage WHERE promo_code = ?", (code,))
            usage_count = c.fetchone()[0]
            
            status = "🔥" if usage_count > 10 else "✅" if usage_count > 0 else "🆕"
            text += f"{i}. {status} **{code}** - {discount}% ({usage_count} исп.)\n"
        
        if len(PROMO_CODES) > 5:
            text += f"\n... и еще {len(PROMO_CODES) - 5} промокодов"
        
        conn.close()
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🎫 Управление промокодами", callback_data="admin_promo"),
            InlineKeyboardButton(text="➕ Создать новый", callback_data="admin_create_promo")
        ],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_quick")]
    ])
    
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()

@admin_router.callback_query(F.data == "admin_back")
async def admin_back(callback: CallbackQuery):
    """Возврат в главную админ панель"""
    await admin_panel(callback.message)
    await callback.answer()

# Системные команды
@admin_router.callback_query(F.data == "system_backup")
async def system_backup(callback: CallbackQuery):
    """Создание бэкапа базы данных"""
    import shutil
    import os
    from datetime import datetime
    
    try:
        backup_name = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        backup_path = f"database/data/{backup_name}"
        
        shutil.copy2("database/data/users.db", backup_path)
        file_size = os.path.getsize(backup_path)
        
        text = (
            f"💾 **БЭКАП СОЗДАН**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"✅ Файл: `{backup_name}`\n"
            f"📦 Размер: {file_size} байт\n"
            f"🕐 Время: {datetime.now().strftime('%H:%M:%S')}"
        )
        
        # Отправляем файл админу
        try:
            with open(backup_path, 'rb') as backup_file:
                await callback.message.answer_document(
                    backup_file,
                    caption="💾 Бэкап базы данных"
                )
        except:
            pass
            
    except Exception as e:
        text = f"❌ **ОШИБКА БЭКАПА**\n\nОшибка: {e}"
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_system")]
    ])
    
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    await callback.answer("Бэкап создан!" if "СОЗДАН" in text else "Ошибка создания бэкапа")

@admin_router.callback_query(F.data == "system_logs")
async def system_logs(callback: CallbackQuery):
    """Показать логи бота"""
    try:
        with open("bot.log", "r", encoding="utf-8") as log_file:
            lines = log_file.readlines()
            last_lines = lines[-30:] if len(lines) > 30 else lines
            
        log_text = "".join(last_lines)
        
        if len(log_text) > 3500:
            log_text = log_text[-3500:]
            log_text = "...\n" + log_text
        
        text = (
            f"📋 **СИСТЕМНЫЕ ЛОГИ**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"```\n{log_text}\n```"
        )
        
    except FileNotFoundError:
        text = "📋 **СИСТЕМНЫЕ ЛОГИ**\n━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n❌ Файл логов не найден"
    except Exception as e:
        text = f"📋 **СИСТЕМНЫЕ ЛОГИ**\n━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n❌ Ошибка чтения логов: {e}"
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔄 Обновить", callback_data="system_logs"),
            InlineKeyboardButton(text="🧹 Очистить логи", callback_data="system_clear_logs")
        ],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_system")]
    ])
    
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()

@admin_router.callback_query(F.data == "system_info")
async def system_info(callback: CallbackQuery):
    """Системная информация"""
    import psutil
    import os
    from datetime import datetime
    
    try:
        # Информация о системе
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Информация о боте
        bot_process = psutil.Process(os.getpid())
        bot_memory = bot_process.memory_info().rss / 1024 / 1024  # MB
        bot_cpu = bot_process.cpu_percent()
        
        # Размер базы данных
        try:
            db_size = os.path.getsize("database/data/users.db") / 1024 / 1024  # MB
        except:
            db_size = 0
        
        text = (
            f"📊 **СИСТЕМНАЯ ИНФОРМАЦИЯ**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🖥️ **Система:**\n"
            f"• CPU: {cpu_percent}%\n"
            f"• RAM: {memory.percent}% ({memory.used // 1024 // 1024}MB / {memory.total // 1024 // 1024}MB)\n"
            f"• Диск: {disk.percent}% ({disk.used // 1024 // 1024 // 1024}GB / {disk.total // 1024 // 1024 // 1024}GB)\n\n"
            f"🤖 **Бот:**\n"
            f"• Память: {bot_memory:.1f}MB\n"
            f"• CPU: {bot_cpu}%\n"
            f"• База данных: {db_size:.1f}MB\n"
            f"• Время работы: {datetime.now().strftime('%H:%M:%S')}"
        )
        
    except Exception as e:
        text = f"📊 **СИСТЕМНАЯ ИНФОРМАЦИЯ**\n━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n❌ Ошибка получения информации: {e}"
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔄 Обновить", callback_data="system_info"),
            InlineKeyboardButton(text="📊 Детальная информация", callback_data="system_detailed")
        ],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_system")]
    ])
    
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()

@admin_router.callback_query(F.data == "system_db_check")
async def system_db_check(callback: CallbackQuery):
    """Проверка целостности базы данных"""
    import sqlite3
    
    try:
        conn = sqlite3.connect("database/data/users.db")
        c = conn.cursor()
        
        # Проверяем целостность
        c.execute("PRAGMA integrity_check")
        integrity_result = c.fetchone()[0]
        
        # Получаем информацию о таблицах
        c.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = c.fetchall()
        
        table_info = []
        for table in tables:
            table_name = table[0]
            c.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = c.fetchone()[0]
            table_info.append(f"• {table_name}: {count} записей")
        
        conn.close()
        
        status = "✅ Исправна" if integrity_result == "ok" else "❌ Повреждена"
        
        text = (
            f"🔍 **ПРОВЕРКА БАЗЫ ДАННЫХ**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📊 **Статус:** {status}\n"
            f"🔧 **Целостность:** {integrity_result}\n\n"
            f"📋 **Таблицы:**\n" + "\n".join(table_info)
        )
        
    except Exception as e:
        text = f"🔍 **ПРОВЕРКА БАЗЫ ДАННЫХ**\n━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n❌ Ошибка проверки: {e}"
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔄 Повторить проверку", callback_data="system_db_check"),
            InlineKeyboardButton(text="💾 Создать бэкап", callback_data="system_backup")
        ],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_system")]
    ])
    
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()

# Быстрые действия
@admin_router.callback_query(F.data == "quick_users")
async def quick_users(callback: CallbackQuery):
    """Последние пользователи"""
    import sqlite3
    
    conn = sqlite3.connect("database/data/users.db")
    c = conn.cursor()
    
    # Последние 10 пользователей
    c.execute("""SELECT user_id, username, reg_date, got_free 
                 FROM users 
                 ORDER BY reg_date DESC 
                 LIMIT 10""")
    recent_users = c.fetchall()
    
    conn.close()
    
    if not recent_users:
        text = "👥 **ПОСЛЕДНИЕ ПОЛЬЗОВАТЕЛИ**\n━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n❌ Пользователей не найдено"
    else:
        text = f"👥 **ПОСЛЕДНИЕ ПОЛЬЗОВАТЕЛИ** ({len(recent_users)})\n━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        
        for i, (user_id, username, reg_date, got_free) in enumerate(recent_users, 1):
            username_display = f"@{username}" if username else f"ID{user_id}"
            free_status = "🎁" if got_free else "💳"
            reg_time = reg_date[:16] if reg_date else "неизвестно"
            
            text += f"{i}. {free_status} {username_display}\n"
            text += f"   📅 {reg_time}\n\n"
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="👥 Управление пользователями", callback_data="admin_users"),
            InlineKeyboardButton(text="🔄 Обновить", callback_data="quick_users")
        ],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_quick")]
    ])
    
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()

@admin_router.callback_query(F.data == "quick_payments")
async def quick_payments(callback: CallbackQuery):
    """Последние платежи"""
    import sqlite3
    
    conn = sqlite3.connect("database/data/users.db")
    c = conn.cursor()
    
    # Последние 10 платежей
    c.execute("""SELECT p.user_id, u.username, p.days, p.status, p.created_at
                 FROM payments p
                 LEFT JOIN users u ON p.user_id = u.user_id
                 ORDER BY p.created_at DESC 
                 LIMIT 10""")
    recent_payments = c.fetchall()
    
    conn.close()
    
    if not recent_payments:
        text = "💳 **ПОСЛЕДНИЕ ПЛАТЕЖИ**\n━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n❌ Платежей не найдено"
    else:
        text = f"💳 **ПОСЛЕДНИЕ ПЛАТЕЖИ** ({len(recent_payments)})\n━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        
        for i, (user_id, username, days, status, created_at) in enumerate(recent_payments, 1):
            username_display = f"@{username}" if username else f"ID{user_id}"
            
            status_emoji = {
                'completed': '✅',
                'pending': '⏳',
                'failed': '❌',
                'cancelled': '🚫'
            }.get(status, '❓')
            
            payment_time = created_at[:16] if created_at else "неизвестно"
            
            text += f"{i}. {status_emoji} {username_display}\n"
            text += f"   📦 {days} дней • 🕐 {payment_time}\n\n"
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💰 Финансы", callback_data="admin_finance"),
            InlineKeyboardButton(text="🔄 Обновить", callback_data="quick_payments")
        ],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_quick")]
    ])
    
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()

@admin_router.callback_query(F.data == "quick_servers")
async def quick_servers(callback: CallbackQuery):
    """Популярные серверы"""
    from config.servers import SERVERS_CONFIG
    import requests
    
    text = f"🔥 **СТАТУС СЕРВЕРОВ** ({len(SERVERS_CONFIG)})\n━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    online_count = 0
    for server_key, server_info in SERVERS_CONFIG.items():
        try:
            response = requests.get(
                f"{server_info['admin_path']}/api/v2/admin/user/", 
                headers={"Hiddify-API-Key": server_info["api_key"]}, 
                timeout=3
            )
            if response.status_code == 200:
                status = "🟢 Онлайн"
                online_count += 1
            else:
                status = f"🟡 Проблемы ({response.status_code})"
        except:
            status = "🔴 Офлайн"
        
        text += f"• **{server_info['name']}**: {status}\n"
    
    text += f"\n📊 Онлайн: **{online_count}/{len(SERVERS_CONFIG)}** серверов"
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔧 Управление серверами", callback_data="admin_servers"),
            InlineKeyboardButton(text="🔄 Обновить", callback_data="quick_servers")
        ],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_quick")]
    ])
    
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()

@admin_router.callback_query(F.data == "quick_issues")
async def quick_issues(callback: CallbackQuery):
    """Проблемы системы"""
    import sqlite3
    from datetime import datetime, timedelta
    
    issues = []
    
    try:
        conn = sqlite3.connect("database/data/users.db")
        c = conn.cursor()
        
        # Проверяем ожидающие платежи старше 1 часа
        hour_ago = (datetime.now() - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
        c.execute("SELECT COUNT(*) FROM payments WHERE status = 'pending' AND created_at < ?", (hour_ago,))
        old_pending = c.fetchone()[0]
        
        if old_pending > 0:
            issues.append(f"⏳ {old_pending} старых ожидающих платежей")
        
        # Проверяем неактивные подписки
        c.execute("SELECT COUNT(*) FROM subscriptions WHERE status != 'active'")
        inactive_subs = c.fetchone()[0]
        
        if inactive_subs > 10:
            issues.append(f"📉 {inactive_subs} неактивных подписок")
        
        # Проверяем пользователей без подписок
        c.execute("""SELECT COUNT(*) FROM users u 
                     LEFT JOIN subscriptions s ON u.user_id = s.user_id 
                     WHERE s.user_id IS NULL AND u.got_free = 0""")
        users_no_subs = c.fetchone()[0]
        
        if users_no_subs > 50:
            issues.append(f"👥 {users_no_subs} пользователей без подписок")
        
        conn.close()
        
    except Exception as e:
        issues.append(f"❌ Ошибка проверки БД: {str(e)[:50]}")
    
    # Проверяем размер логов
    try:
        import os
        log_size = os.path.getsize("bot.log") / 1024 / 1024  # MB
        if log_size > 10:
            issues.append(f"📋 Большой файл логов ({log_size:.1f}MB)")
    except:
        pass
    
    if not issues:
        text = "⚠️ **ПРОБЛЕМЫ СИСТЕМЫ**\n━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n✅ Проблем не обнаружено!\nСистема работает стабильно."
    else:
        text = f"⚠️ **ПРОБЛЕМЫ СИСТЕМЫ** ({len(issues)})\n━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        for i, issue in enumerate(issues, 1):
            text += f"{i}. {issue}\n"
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔧 Системные команды", callback_data="admin_system"),
            InlineKeyboardButton(text="🔄 Обновить", callback_data="quick_issues")
        ],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_quick")]
    ])
    
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()

@admin_router.callback_query(F.data == "system_cache")
async def system_cache(callback: CallbackQuery):
    """Очистка кэша"""
    import gc
    import os
    
    try:
        # Принудительная сборка мусора
        collected = gc.collect()
        
        # Очищаем временные файлы
        temp_files = 0
        try:
            for file in os.listdir("."):
                if file.endswith(('.tmp', '.temp', '.log.1', '.log.2')):
                    os.remove(file)
                    temp_files += 1
        except:
            pass
        
        text = (
            f"🧹 **ОЧИСТКА КЭША**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"✅ Операция завершена:\n"
            f"• Собрано объектов: {collected}\n"
            f"• Удалено временных файлов: {temp_files}\n"
            f"• Память освобождена"
        )
        
    except Exception as e:
        text = f"🧹 **ОЧИСТКА КЭША**\n━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n❌ Ошибка очистки: {e}"
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_system")]
    ])
    
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    await callback.answer("Кэш очищен!" if "завершена" in text else "Ошибка очистки")

@admin_router.callback_query(F.data == "system_clear_logs")
async def system_clear_logs(callback: CallbackQuery):
    """Очистка логов"""
    try:
        with open("bot.log", "w", encoding="utf-8") as log_file:
            log_file.write(f"# Логи очищены {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        text = (
            f"🧹 **ЛОГИ ОЧИЩЕНЫ**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"✅ Файл логов очищен\n"
            f"🕐 Время: {datetime.now().strftime('%H:%M:%S')}"
        )
        
    except Exception as e:
        text = f"🧹 **ОЧИСТКА ЛОГОВ**\n━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n❌ Ошибка: {e}"
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📋 Показать логи", callback_data="system_logs"),
            InlineKeyboardButton(text="🔙 Назад", callback_data="admin_system")
        ]
    ])
    
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    await callback.answer("Логи очищены!" if "ОЧИЩЕНЫ" in text else "Ошибка очистки")