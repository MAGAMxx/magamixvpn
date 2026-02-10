@echo off
chcp 65001 >nul
title MAGAM VPN Bot v2.0
color 0A

echo.
echo ╔══════════════════════════════════════╗
echo ║          MAGAM VPN BOT v2.0          ║
echo ║        Telegram VPN Service          ║
echo ╚══════════════════════════════════════╝
echo.

echo [INFO] Проверяем зависимости...

REM Проверяем наличие Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python не найден! Установите Python 3.8+
    pause
    exit /b 1
)

REM Проверяем наличие виртуального окружения
if not exist "venv\Scripts\activate.bat" (
    echo [INFO] Создаем виртуальное окружение...
    python -m venv venv
    if errorlevel 1 (
        echo [ERROR] Не удалось создать виртуальное окружение
        pause
        exit /b 1
    )
)

echo [INFO] Активируем виртуальное окружение...
call venv\Scripts\activate.bat

REM Проверяем requirements.txt
if exist "requirements.txt" (
    echo [INFO] Проверяем зависимости...
    
    REM Проверяем установлен ли aiogram
    python -c "import aiogram" >nul 2>&1
    if errorlevel 1 (
        echo [INFO] Устанавливаем зависимости...
        pip install -r requirements.txt
        if errorlevel 1 (
            echo [ERROR] Не удалось установить зависимости
            pause
            exit /b 1
        )
    ) else (
        echo [INFO] Зависимости уже установлены
    )
) else (
    echo [WARNING] Файл requirements.txt не найден
)

echo [INFO] Запускаем бота...
echo.

REM Запускаем бота с правильной кодировкой
python main.py

echo.
if errorlevel 1 (
    echo [ERROR] Бот завершился с ошибкой
) else (
    echo [INFO] Бот завершил работу
)

echo.
echo Нажмите любую клавишу для выхода...
pause >nul