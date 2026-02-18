import sqlite3
import shutil
import os
from datetime import datetime, timedelta
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from config.settings import ADMIN_IDS

admin_router = Router()

admin_router.message.filter(lambda message: message.from_user.id in ADMIN_IDS)
admin_router.callback_query.filter(lambda callback: callback.from_user.id in ADMIN_IDS)

async def show_admin_panel(target, is_callback=False):
    text = (
        "🛡 **ПАНЕЛЬ УПРАВЛЕНИЯ**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📅 {datetime.now().strftime('%d.%m.%Y • %H:%M')}\n\n"
        "Выберите раздел:"
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
            InlineKeyboardButton(text="⚙️ Система", callback_data="admin_system"),
            InlineKeyboardButton(text="⚡ Быстрые действия", callback_data="admin_quick")
        ]
    ])

    if is_callback:
        await target.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    else:
        await target.answer(text, reply_markup=kb, parse_mode="Markdown")

@admin_router.message(Command("admin"))
async def admin_panel(message: Message):
    await show_admin_panel(message, is_callback=False)

@admin_router.callback_query(F.data == "admin_back")
async def admin_back(callback: CallbackQuery):
    await show_admin_panel(callback, is_callback=True)
    await callback.answer()

@admin_router.callback_query(F.data == "admin_system")
async def admin_system(callback: CallbackQuery):
    text = (
        "⚙️ **СИСТЕМА**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Управление и обслуживание:"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💾 Бэкап БД", callback_data="system_backup"),
            InlineKeyboardButton(text="📊 Инфо о системе", callback_data="system_info")
        ],
        [
            InlineKeyboardButton(text="🔍 Проверка БД", callback_data="system_db_check"),
            InlineKeyboardButton(text="🧹 Очистка бэкапов", callback_data="system_cleanup")
        ],
        [
            InlineKeyboardButton(text="📋 Логи", callback_data="system_logs"),
            InlineKeyboardButton(text="🗑 Очистить логи", callback_data="system_clear_logs")
        ],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")]
    ])

    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()

LOG_FILE = "bot.log"

@admin_router.callback_query(F.data == "system_logs")
async def system_logs(callback: CallbackQuery):
    if not os.path.exists(LOG_FILE):
        await callback.message.edit_text(
            "📋 **ЛОГИ БОТА**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "📭 Файл логов не найден\n\n"
            "_Логи появятся после запуска бота через pm2_",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_system")]
            ]),
            parse_mode="Markdown"
        )
        await callback.answer()
        return

    file_size = os.path.getsize(LOG_FILE)
    if file_size > 1024 * 1024:
        size_str = f"{file_size / (1024 * 1024):.1f} МБ"
    elif file_size > 1024:
        size_str = f"{file_size / 1024:.1f} КБ"
    else:
        size_str = f"{file_size} Б"

    with open(LOG_FILE, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()

    error_lines = []
    for line in lines:
        line_upper = line.upper()
        if "ERROR" in line_upper or "WARNING" in line_upper or "WARN" in line_upper or "CRITICAL" in line_upper or "TRACEBACK" in line_upper or "EXCEPTION" in line_upper:
            error_lines.append(line.rstrip())

    total_errors = len(error_lines)

    if not error_lines:
        log_block = "# ✅ Ошибок и предупреждений нет"
    else:
        last_errors = error_lines[-20:]
        formatted = []
        for line in last_errors:
            line_upper = line.upper()
            if "ERROR" in line_upper or "CRITICAL" in line_upper or "EXCEPTION" in line_upper:
                formatted.append(f"# [ERROR] {line[:100]}")
            elif "WARNING" in line_upper or "WARN" in line_upper:
                formatted.append(f"# [WARN]  {line[:100]}")
            elif "TRACEBACK" in line_upper:
                formatted.append(f"# [TRACE] {line[:100]}")
            else:
                formatted.append(f"# {line[:100]}")
        log_block = "\n".join(formatted)

    header = (
        "📋 **ЛОГИ БОТА**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📁 Размер: `{size_str}`\n"
        f"📝 Строк: `{len(lines)}`\n"
        f"⚠️ Ошибок: `{total_errors}`\n\n"
    )

    max_block_len = 4000 - len(header) - 20
    if len(log_block) > max_block_len:
        log_block = log_block[:max_block_len] + "\n# ... обрезано"

    text = header + f"```python\n{log_block}\n```"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔄 Обновить", callback_data="system_logs"),
            InlineKeyboardButton(text="📄 Все логи", callback_data="system_logs_full")
        ],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_system")]
    ])

    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()

@admin_router.callback_query(F.data == "system_logs_full")
async def system_logs_full(callback: CallbackQuery):
    if not os.path.exists(LOG_FILE):
        await callback.answer("📭 Файл логов не найден", show_alert=True)
        return

    try:
        from aiogram.types import BufferedInputFile
        with open(LOG_FILE, "rb") as f:
            file_data = f.read()
        
        doc = BufferedInputFile(file_data, filename=f"bot_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
        await callback.message.answer_document(doc, caption="📋 Полный файл логов бота")
        await callback.answer("📄 Файл отправлен")
    except Exception as e:
        await callback.answer(f"❌ Ошибка: {e}", show_alert=True)

@admin_router.callback_query(F.data == "system_clear_logs")
async def system_clear_logs(callback: CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Да, очистить", callback_data="system_clear_logs_confirm"),
            InlineKeyboardButton(text="❌ Отмена", callback_data="admin_system")
        ]
    ])

    await callback.message.edit_text(
        "🗑 **ОЧИСТКА ЛОГОВ**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "⚠️ Вы уверены, что хотите очистить файл логов?\n\n"
        "_Это действие нельзя отменить_",
        reply_markup=kb,
        parse_mode="Markdown"
    )
    await callback.answer()

@admin_router.callback_query(F.data == "system_clear_logs_confirm")
async def system_clear_logs_confirm(callback: CallbackQuery):
    try:
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE, "w", encoding="utf-8") as f:
                f.write("")
        
        await callback.message.edit_text(
            "✅ **ЛОГИ ОЧИЩЕНЫ**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🕐 {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_system")]
            ]),
            parse_mode="Markdown"
        )
        await callback.answer("✅ Готово")
    except Exception as e:
        await callback.answer(f"❌ Ошибка: {e}", show_alert=True)

@admin_router.callback_query(F.data == "admin_quick")
async def admin_quick(callback: CallbackQuery):
    text = (
        "⚡ **БЫСТРЫЕ ДЕЙСТВИЯ**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Часто используемые команды:"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📊 Быстрая статистика", callback_data="quick_stats"),
            InlineKeyboardButton(text="👥 Новые юзеры", callback_data="quick_users")
        ],
        [
            InlineKeyboardButton(text="💳 Последние платежи", callback_data="quick_payments"),
            InlineKeyboardButton(text="🔥 Статус серверов", callback_data="quick_servers")
        ],
        [
            InlineKeyboardButton(text="⚠️ Проблемы", callback_data="quick_issues"),
            InlineKeyboardButton(text="🎫 Промокоды", callback_data="quick_promos")
        ],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")]
    ])

    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()

@admin_router.callback_query(F.data == "quick_stats")
async def quick_stats(callback: CallbackQuery):
    conn = sqlite3.connect("database/data/users.db")
    c = conn.cursor()

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

    activity_percent = (active_subs / max(total_users, 1)) * 100

    text = (
        f"⚡ **БЫСТРАЯ СТАТИСТИКА**\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"```\n"
        f"Показатель     |  Кол-во\n"
        f"---------------|--------\n"
        f"👥 Всего юзеров |  {total_users:>5}\n"
        f"✅ Актив. подп.  |  {active_subs:>5}\n"
        f"📈 Конверсия    | {activity_percent:>5.1f}%\n"
        f"🆕 Сегодня      |  {today_users:>5}\n"
        f"---------------|--------\n"
        f"💳 Завершённых  |  {completed_payments:>5}\n"
        f"⏳ Ожидающих    |  {pending_payments:>5}\n"
        f"```"
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
    conn = sqlite3.connect("database/data/users.db")
    c = conn.cursor()

    try:
        c.execute("SELECT code, discount FROM promo_codes WHERE is_active = 1")
        promo_codes = c.fetchall()
    except:
        promo_codes = []

    if not promo_codes:
        text = "🎫 **ПРОМОКОДЫ**\n━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n❌ Активных промокодов нет"
    else:
        text = f"🎫 **АКТИВНЫЕ ПРОМОКОДЫ** ({len(promo_codes)})\n━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"

        for i, (code, discount) in enumerate(promo_codes[:5], 1):
            try:
                c.execute("SELECT COUNT(*) FROM promo_usage WHERE promo_code = ?", (code,))
                usage_count = c.fetchone()[0]
            except:
                usage_count = 0

            status = "🔥" if usage_count > 10 else "✅" if usage_count > 0 else "🆕"
            text += f"{i}. {status} **{code}** — {discount}% ({usage_count} исп.)\n"

        if len(promo_codes) > 5:
            text += f"\n... и ещё {len(promo_codes) - 5} промокодов"

    conn.close()

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🎫 Управление", callback_data="admin_promo"),
            InlineKeyboardButton(text="➕ Создать", callback_data="admin_create_promo")
        ],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_quick")]
    ])

    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()

@admin_router.callback_query(F.data == "system_backup")
async def system_backup(callback: CallbackQuery):
    try:
        os.makedirs("database/data/backups", exist_ok=True)
        backup_name = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        backup_path = f"database/data/backups/{backup_name}"

        shutil.copy2("database/data/users.db", backup_path)
        file_size = os.path.getsize(backup_path)

        size_str = f"{file_size / 1024:.1f} KB" if file_size > 1024 else f"{file_size} байт"

        text = (
            f"💾 **БЭКАП СОЗДАН**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"✅ Статус: Успешно\n"
            f"📄 Файл: `{backup_name}`\n"
            f"📦 Размер: {size_str}\n"
            f"🕐 Время: {datetime.now().strftime('%H:%M:%S')}"
        )

        try:
            from aiogram.types import FSInputFile
            doc = FSInputFile(backup_path, filename=backup_name)
            await callback.message.answer_document(doc, caption="💾 Бэкап базы данных")
        except:
            pass

    except Exception as e:
        text = f"❌ **ОШИБКА БЭКАПА**\n\nОшибка: {e}"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_system")]
    ])

    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()

@admin_router.callback_query(F.data == "system_info")
async def system_info(callback: CallbackQuery):
    import psutil

    try:
        cpu_percent = psutil.cpu_percent(interval=0.5)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')

        bot_process = psutil.Process(os.getpid())
        bot_memory = bot_process.memory_info().rss / 1024 / 1024

        try:
            db_size = os.path.getsize("database/data/users.db") / 1024
            db_str = f"{db_size:.1f} KB" if db_size < 1024 else f"{db_size/1024:.1f} MB"
        except:
            db_str = "N/A"

        uptime = datetime.now() - datetime.fromtimestamp(bot_process.create_time())
        hours, remainder = divmod(int(uptime.total_seconds()), 3600)
        minutes, _ = divmod(remainder, 60)

        text = (
            f"📊 **СИСТЕМНАЯ ИНФОРМАЦИЯ**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🖥️ **Сервер**\n"
            f"┣ CPU: {cpu_percent}%\n"
            f"┣ RAM: {memory.percent}% ({memory.used // 1024 // 1024}MB / {memory.total // 1024 // 1024}MB)\n"
            f"┗ Диск: {disk.percent}%\n\n"
            f"🤖 **Бот**\n"
            f"┣ Память: {bot_memory:.1f} MB\n"
            f"┣ Аптайм: {hours}ч {minutes}м\n"
            f"┗ БД: {db_str}"
        )

    except Exception as e:
        text = f"📊 **СИСТЕМНАЯ ИНФОРМАЦИЯ**\n━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n❌ Ошибка: {e}"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Обновить", callback_data="system_info")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_system")]
    ])

    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()

@admin_router.callback_query(F.data == "system_db_check")
async def system_db_check(callback: CallbackQuery):
    try:
        conn = sqlite3.connect("database/data/users.db")
        c = conn.cursor()

        c.execute("PRAGMA integrity_check")
        integrity_result = c.fetchone()[0]

        c.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = c.fetchall()

        table_info = []
        for table in tables:
            table_name = table[0]
            c.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = c.fetchone()[0]
            safe_name = table_name.replace("_", "\\_")
            table_info.append(f"┣ {safe_name}: **{count}** записей")

        if table_info:
            table_info[-1] = table_info[-1].replace("┣", "┗")

        conn.close()

        status = "✅ Исправна" if integrity_result == "ok" else "❌ Повреждена"

        text = (
            f"🔍 **ПРОВЕРКА БАЗЫ ДАННЫХ**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📊 Статус: {status}\n\n"
            f"📋 **Таблицы:**\n" + "\n".join(table_info)
        )

    except Exception as e:
        text = f"🔍 **ПРОВЕРКА БД**\n━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n❌ Ошибка: {e}"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔄 Повторить", callback_data="system_db_check"),
            InlineKeyboardButton(text="💾 Бэкап", callback_data="system_backup")
        ],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_system")]
    ])

    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()

@admin_router.callback_query(F.data == "system_cleanup")
async def system_cleanup(callback: CallbackQuery):
    backup_dir = "database/data/backups"
    try:
        if not os.path.exists(backup_dir):
            text = "🧹 **ОЧИСТКА**\n━━━━━━━━━━━━━━━━━━━━━━━━━━\n\nНет бэкапов для очистки."
        else:
            files = sorted(os.listdir(backup_dir))
            if len(files) <= 3:
                text = f"🧹 **ОЧИСТКА**\n━━━━━━━━━━━━━━━━━━━━━━━━━━\n\nБэкапов: {len(files)} (макс. 3). Очистка не требуется."
            else:
                to_delete = files[:-3]
                for f in to_delete:
                    os.remove(os.path.join(backup_dir, f))
                text = f"🧹 **ОЧИСТКА**\n━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n✅ Удалено {len(to_delete)} старых бэкапов.\nОставлено последних 3."
    except Exception as e:
        text = f"🧹 **ОЧИСТКА**\n━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n❌ Ошибка: {e}"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_system")]
    ])

    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()

@admin_router.callback_query(F.data == "quick_users")
async def quick_users(callback: CallbackQuery):
    conn = sqlite3.connect("database/data/users.db")
    c = conn.cursor()

    c.execute("""SELECT user_id, username, reg_date, got_free 
                 FROM users 
                 ORDER BY reg_date DESC 
                 LIMIT 10""")
    recent_users = c.fetchall()
    conn.close()

    if not recent_users:
        text = "👥 **НОВЫЕ ПОЛЬЗОВАТЕЛИ**\n━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n❌ Пользователей не найдено"
    else:
        text = f"👥 **НОВЫЕ ПОЛЬЗОВАТЕЛИ**\n━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"

        for i, (user_id, username, reg_date, got_free) in enumerate(recent_users, 1):
            username_display = f"@{username}" if username and username != "нет" else f"`{user_id}`"
            free_icon = "🎁" if got_free else "👤"
            reg_time = reg_date[:16] if reg_date else "—"
            text += f"{free_icon} {i}. {username_display}\n     📅 {reg_time}\n"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="👥 Управление", callback_data="admin_users"),
            InlineKeyboardButton(text="🔄 Обновить", callback_data="quick_users")
        ],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_quick")]
    ])

    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()

@admin_router.callback_query(F.data == "quick_payments")
async def quick_payments(callback: CallbackQuery):
    conn = sqlite3.connect("database/data/users.db")
    c = conn.cursor()

    c.execute("""SELECT p.user_id, u.username, p.tarif, p.days, p.status, p.created_at
                 FROM payments p
                 LEFT JOIN users u ON p.user_id = u.user_id
                 ORDER BY p.created_at DESC 
                 LIMIT 10""")
    recent_payments = c.fetchall()
    conn.close()

    if not recent_payments:
        text = "💳 **ПОСЛЕДНИЕ ПЛАТЕЖИ**\n━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n❌ Платежей нет"
    else:
        text = f"💳 **ПОСЛЕДНИЕ ПЛАТЕЖИ**\n━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        text += "```\n"
        text += f" #  | Ст.  | Юзер          | Тариф     | Дата\n"
        text += f"----|------|---------------|-----------|------\n"

        status_map = {'completed': 'OK', 'pending': 'WAIT', 'failed': 'FAIL', 'cancelled': 'CANC'}

        for i, (user_id, username, tarif, days, status, created_at) in enumerate(recent_payments, 1):
            st = status_map.get(status, '?')
            user_display = (f"@{username}" if username and username != "нет" else str(user_id))[:13]
            tarif_display = (tarif or f"{days}д")[:9]
            payment_time = created_at[5:16] if created_at else "—"
            text += f" {i:<2} | {st:<4} | {user_display:<13} | {tarif_display:<9} | {payment_time}\n"

        text += "```"

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
    from config.servers import SERVERS_CONFIG
    import requests as req

    text = f"🔥 **СТАТУС СЕРВЕРОВ**\n━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"

    online_count = 0
    for server_key, server_info in SERVERS_CONFIG.items():
        try:
            response = req.get(
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

        text += f"┣ **{server_key}** {server_info['name']}: {status}\n"

    text += f"\n📊 Онлайн: **{online_count}/{len(SERVERS_CONFIG)}**"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔧 Серверы", callback_data="admin_servers"),
            InlineKeyboardButton(text="🔄 Обновить", callback_data="quick_servers")
        ],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_quick")]
    ])

    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()

@admin_router.callback_query(F.data == "quick_issues")
async def quick_issues(callback: CallbackQuery):
    issues = []

    try:
        conn = sqlite3.connect("database/data/users.db")
        c = conn.cursor()

        hour_ago = (datetime.now() - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
        c.execute("SELECT COUNT(*) FROM payments WHERE status = 'pending' AND created_at < ?", (hour_ago,))
        old_pending = c.fetchone()[0]
        if old_pending > 0:
            issues.append(f"⚠️ {old_pending} платежей ожидают более 1 часа")

        c.execute("SELECT COUNT(*) FROM subscriptions WHERE status = 'active'")
        active = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM users")
        total = c.fetchone()[0]
        if total > 0 and (active / total) < 0.05:
            issues.append("📉 Конверсия ниже 5%")

        conn.close()
    except:
        pass

    from config.servers import SERVERS_CONFIG
    import requests as req
    for server_key, server_info in SERVERS_CONFIG.items():
        try:
            r = req.get(
                f"{server_info['admin_path']}/api/v2/admin/user/",
                headers={"Hiddify-API-Key": server_info["api_key"]},
                timeout=3
            )
            if r.status_code != 200:
                issues.append(f"🔴 Сервер {server_key} — проблемы ({r.status_code})")
        except:
            issues.append(f"🔴 Сервер {server_key} — недоступен")

    if not issues:
        text = "⚠️ **ПРОБЛЕМЫ**\n━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n✅ Всё в порядке! Проблем не обнаружено."
    else:
        text = f"⚠️ **ПРОБЛЕМЫ** ({len(issues)})\n━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        text += "\n".join(issues)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Обновить", callback_data="quick_issues")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_quick")]
    ])

    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()
