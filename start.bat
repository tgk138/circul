@echo off
chcp 65001 >nul
REM Скрипт для запуска Telegram бота в виртуальном окружении

echo ========================================
echo Запуск Telegram бота для кружочков
echo ========================================
echo.

REM Проверяем существование venv
if not exist "venv\" (
    echo [ОШИБКА] Виртуальное окружение не найдено!
    echo Создаю виртуальное окружение...
    python -m venv venv
    if errorlevel 1 (
        echo [ОШИБКА] Не удалось создать venv. Убедитесь, что Python установлен.
        pause
        exit /b 1
    )
    echo [OK] Виртуальное окружение создано
)

REM Активируем venv
echo Активирую виртуальное окружение...
call venv\Scripts\activate.bat

REM Проверяем установлены ли зависимости
echo Проверяю зависимости...
pip show python-telegram-bot >nul 2>&1
if errorlevel 1 (
    echo [ВНИМАНИЕ] Зависимости не установлены. Устанавливаю...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo [ОШИБКА] Не удалось установить зависимости.
        pause
        exit /b 1
    )
    echo [OK] Зависимости установлены
)

REM Проверяем наличие .env файла
if not exist ".env" (
    echo [ВНИМАНИЕ] Файл .env не найден!
    echo Создайте файл .env с токеном бота:
    echo BOT_TOKEN=your_token_here
    echo.
    pause
)

REM Запускаем бота
echo.
echo ========================================
echo Запускаю бота...
echo ========================================
echo.
python bot.py

REM Если бот завершился с ошибкой, оставляем окно открытым
if errorlevel 1 (
    echo.
    echo [ОШИБКА] Бот завершился с ошибкой.
    pause
)

