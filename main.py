import asyncio
import sys
import os
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from config.settings import BOT_TOKEN
from database.models import init_db
from handlers.user_handlers import user_router
from handlers.payment_handlers import payment_router, yookassa_payment_watcher
from admin import admin_routers

# Настройка кодировки для Windows
if sys.platform == "win32":
    os.system("chcp 65001 > nul")

# Устанавливаем кодировку для stdout
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

def print_status(message):
    """Безопасный вывод статуса"""
    try:
        print(f"[INFO] {message}")
    except UnicodeEncodeError:
        print(f"[INFO] {message.encode('ascii', 'ignore').decode('ascii')}")

async def main():
    """Главная функция запуска бота"""
    try:
        print_status("Инициализация базы данных...")
        init_db()
        
        print_status("Создание бота и диспетчера...")
        bot = Bot(token=BOT_TOKEN)
        storage = MemoryStorage()
        dp = Dispatcher(storage=storage)
        
        print_status("Подключение роутеров...")
        dp.include_router(user_router)
        dp.include_router(payment_router)

        asyncio.create_task(yookassa_payment_watcher(bot))

        
        # Подключение всех админ роутеров
        for router in admin_routers:
            dp.include_router(router)
        
        print_status("Запуск бота...")
        print_status("Бот успешно запущен! Нажмите Ctrl+C для остановки")
        
        await dp.start_polling(bot)
        
    except KeyboardInterrupt:
        print_status("Получен сигнал остановки...")
    except Exception as e:
        print(f"[ERROR] Ошибка запуска бота: {e}")
    finally:
        print_status("Завершение работы бота...")

if __name__ == "__main__":
    asyncio.run(main())
