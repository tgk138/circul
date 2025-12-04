@echo off
REM Скрипт для первоначальной настройки проекта

echo ========================================
echo Настройка проекта Telegram бота
echo ========================================
echo.

REM Проверяем Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ОШИБКА] Python не найден! Установите Python 3.10 или выше.
    pause
    exit /b 1
)

echo [OK] Python найден
python --version

REM Создаём venv если его нет
if not exist "venv\" (
    echo.
    echo Создаю виртуальное окружение...
    python -m venv venv
    if errorlevel 1 (
        echo [ОШИБКА] Не удалось создать venv.
        pause
        exit /b 1
    )
    echo [OK] Виртуальное окружение создано
) else (
    echo [OK] Виртуальное окружение уже существует
)

REM Активируем venv
echo.
echo Активирую виртуальное окружение...
call venv\Scripts\activate.bat

REM Обновляем pip
echo.
echo Обновляю pip...
python -m pip install --upgrade pip

REM Устанавливаем зависимости
echo.
echo Устанавливаю зависимости...
pip install -r requirements.txt
if errorlevel 1 (
    echo [ОШИБКА] Не удалось установить зависимости.
    pause
    exit /b 1
)

echo [OK] Зависимости установлены

REM Проверяем .env
echo.
if not exist ".env" (
    echo [ВНИМАНИЕ] Файл .env не найден!
    echo Создаю шаблон .env...
    (
        echo BOT_TOKEN=your_bot_token_here
    ) > .env
    echo [OK] Файл .env создан. Отредактируйте его и вставьте токен бота.
) else (
    echo [OK] Файл .env существует
)

echo.
echo ========================================
echo Настройка завершена!
echo ========================================
echo.
echo Следующие шаги:
echo 1. Отредактируйте файл .env и вставьте токен бота
echo 2. Убедитесь, что FFmpeg установлен и доступен
echo 3. Запустите бота командой: start.bat
echo.
pause

