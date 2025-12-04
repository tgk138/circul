# Скрипт для запуска Telegram бота в виртуальном окружении (PowerShell)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Запуск Telegram бота для кружочков" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Проверяем существование venv
if (-not (Test-Path "venv")) {
    Write-Host "[ОШИБКА] Виртуальное окружение не найдено!" -ForegroundColor Red
    Write-Host "Создаю виртуальное окружение..." -ForegroundColor Yellow
    python -m venv venv
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ОШИБКА] Не удалось создать venv. Убедитесь, что Python установлен." -ForegroundColor Red
        Read-Host "Нажмите Enter для выхода"
        exit 1
    }
    Write-Host "[OK] Виртуальное окружение создано" -ForegroundColor Green
}

# Активируем venv
Write-Host "Активирую виртуальное окружение..." -ForegroundColor Yellow
& "venv\Scripts\Activate.ps1"

# Проверяем установлены ли зависимости
Write-Host "Проверяю зависимости..." -ForegroundColor Yellow
$package = pip show python-telegram-bot 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ВНИМАНИЕ] Зависимости не установлены. Устанавливаю..." -ForegroundColor Yellow
    pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ОШИБКА] Не удалось установить зависимости." -ForegroundColor Red
        Read-Host "Нажмите Enter для выхода"
        exit 1
    }
    Write-Host "[OK] Зависимости установлены" -ForegroundColor Green
}

# Проверяем наличие .env файла
if (-not (Test-Path ".env")) {
    Write-Host "[ВНИМАНИЕ] Файл .env не найден!" -ForegroundColor Yellow
    Write-Host "Создайте файл .env с токеном бота:" -ForegroundColor Yellow
    Write-Host "BOT_TOKEN=your_token_here" -ForegroundColor Yellow
    Write-Host ""
    Read-Host "Нажмите Enter для продолжения"
}

# Запускаем бота
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Запускаю бота..." -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

python bot.py

# Если бот завершился с ошибкой
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "[ОШИБКА] Бот завершился с ошибкой." -ForegroundColor Red
    Read-Host "Нажмите Enter для выхода"
}

