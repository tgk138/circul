"""Telegram бот для нарезки видео на кружочки"""

import os
import logging
from pathlib import Path
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv
from video_processor import process_video_to_circles, cut_video_to_circles, check_ffmpeg_available
import config

# Загрузка переменных окружения
load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN')

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не найден в переменных окружения. Создайте файл .env с BOT_TOKEN=your_token")

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /start"""
    await update.message.reply_text(
        "Привет! 👋\n\n"
        "Я нарезаю видео на кружочки по 10 секунд! 🎬\n\n"
        "Ты можешь:\n"
        "• Отправить ссылку на видео (YouTube, TikTok, Instagram и другие)\n"
        "• Или отправить видео файл напрямую в чат\n\n"
        "Я обработаю его и отправлю обратно в виде кружочков!"
    )


async def handle_video_file(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик видео файлов, отправленных напрямую в бот"""
    chat_id = update.message.chat_id
    logger.info(f"Получен видео файл от пользователя {chat_id}, тип контента: {update.message.content_type}")
    
    # Проверяем разные типы видео
    video = update.message.video or update.message.video_note
    document = update.message.document
    
    # Если это документ, проверяем, что это видео
    if document and document.mime_type and document.mime_type.startswith('video/'):
        video = document
        logger.info(f"Видео получено как документ: {document.file_name}, размер: {document.file_size}")
    elif not video:
        logger.warning(f"Не удалось получить видео из сообщения. Тип: {update.message.content_type}")
        await update.message.reply_text("❌ Не удалось получить видео из сообщения.")
        return
    
    # Отправляем сообщение о начале обработки
    status_message = await update.message.reply_text("⏳ Скачиваю и обрабатываю видео...")
    
    video_files = []
    temp_video_path = None
    
    try:
        # Скачиваем видео файл из Telegram
        file = await context.bot.get_file(video.file_id)
        
        # Определяем расширение файла
        file_ext = '.mp4'
        if hasattr(video, 'mime_type') and video.mime_type:
            if 'webm' in video.mime_type:
                file_ext = '.webm'
            elif 'quicktime' in video.mime_type or 'mov' in video.mime_type:
                file_ext = '.mov'
        
        temp_video_path = Path(config.TEMP_VIDEOS_DIR) / f"telegram_video_{chat_id}_{video.file_id}{file_ext}"
        temp_video_path.parent.mkdir(exist_ok=True)
        
        await file.download_to_drive(custom_path=str(temp_video_path))
        logger.info(f"Видео скачано: {temp_video_path}")
        
        # Обрабатываем видео
        video_files = await cut_video_to_circles(str(temp_video_path), config.DEFAULT_SEGMENT_DURATION)
        
        if not video_files:
            await status_message.edit_text("❌ Не удалось обработать видео. Проверь ссылку.")
            return
        
        # Отправляем каждый кружочек
        total = len(video_files)
        for i, video_path in enumerate(video_files, 1):
            try:
                with open(video_path, 'rb') as video_file:
                    await update.message.reply_video_note(
                        video_note=video_file,
                        duration=None  # Telegram сам определит длительность
                    )
                
                # Удаляем временный файл после успешной отправки
                try:
                    os.remove(video_path)
                except Exception as e:
                    logger.warning(f"Не удалось удалить файл {video_path}: {e}")
                
                logger.info(f"Отправлен кружочек {i}/{total} пользователю {chat_id}")
                
            except Exception as e:
                logger.error(f"Ошибка отправки кружочка {i}: {e}")
                # Продолжаем отправку остальных, даже если один не удался
                try:
                    os.remove(video_path)
                except:
                    pass
        
        # Обновляем статус
        await status_message.edit_text(f"✅ Готово! Отправлено {total} кружочков!")
        logger.info(f"Успешно обработано видео для пользователя {chat_id}: {total} кружочков")
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Ошибка обработки видео для пользователя {chat_id}: {error_msg}")
        
        # Пытаемся дать более понятное сообщение об ошибке
        if "FFmpeg" in error_msg or "ffprobe" in error_msg:
            user_error = "❌ Ошибка обработки видео. Убедитесь, что FFmpeg установлен и доступен."
        elif "yt-dlp" in error_msg.lower() or "download" in error_msg.lower():
            user_error = "❌ Не удалось скачать видео. Проверь ссылку или попробуй другую платформу."
        else:
            user_error = f"❌ Ошибка: {error_msg}"
        
        await status_message.edit_text(user_error)
        
        # Очищаем временные файлы в случае ошибки
        for video_path in video_files:
            try:
                if os.path.exists(video_path):
                    os.remove(video_path)
            except:
                pass
        
        # Удаляем исходный файл из Telegram
        if temp_video_path and os.path.exists(temp_video_path):
            try:
                os.remove(temp_video_path)
            except:
                pass


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик текстовых сообщений (ссылок на видео)"""
    if not update.message or not update.message.text:
        logger.warning(f"Получено сообщение без текста от пользователя {update.message.chat_id if update.message else 'unknown'}")
        return
    
    message_text = update.message.text.strip()
    
    # Проверяем, что это похоже на ссылку
    if not (message_text.startswith('http://') or message_text.startswith('https://')):
        await update.message.reply_text(
            "❌ Пожалуйста, отправь ссылку на видео (начинается с http:// или https://)\n\n"
            "Или отправь видео файл напрямую в чат!"
        )
        return
    
    chat_id = update.message.chat_id
    logger.info(f"Получена ссылка от пользователя {chat_id}: {message_text}")
    
    # Отправляем сообщение о начале обработки
    status_message = await update.message.reply_text("⏳ Скачиваю и обрабатываю видео...")
    
    video_files = []
    try:
        # Обрабатываем видео
        video_files = await process_video_to_circles(message_text, config.DEFAULT_SEGMENT_DURATION)
        
        if not video_files:
            await status_message.edit_text("❌ Не удалось обработать видео. Проверь ссылку.")
            return
        
        # Отправляем каждый кружочек
        total = len(video_files)
        for i, video_path in enumerate(video_files, 1):
            try:
                with open(video_path, 'rb') as video_file:
                    await update.message.reply_video_note(
                        video_note=video_file,
                        duration=None  # Telegram сам определит длительность
                    )
                
                # Удаляем временный файл после успешной отправки
                try:
                    os.remove(video_path)
                except Exception as e:
                    logger.warning(f"Не удалось удалить файл {video_path}: {e}")
                
                logger.info(f"Отправлен кружочек {i}/{total} пользователю {chat_id}")
                
            except Exception as e:
                logger.error(f"Ошибка отправки кружочка {i}: {e}")
                # Продолжаем отправку остальных, даже если один не удался
                try:
                    os.remove(video_path)
                except:
                    pass
        
        # Обновляем статус
        await status_message.edit_text(f"✅ Готово! Отправлено {total} кружочков!")
        logger.info(f"Успешно обработано видео для пользователя {chat_id}: {total} кружочков")
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Ошибка обработки видео для пользователя {chat_id}: {error_msg}")
        
        # Пытаемся дать более понятное сообщение об ошибке
        if "FFmpeg" in error_msg or "ffprobe" in error_msg:
            user_error = "❌ Ошибка обработки видео. Убедитесь, что FFmpeg установлен и доступен."
        elif "yt-dlp" in error_msg.lower() or "download" in error_msg.lower():
            user_error = "❌ Не удалось скачать видео. Проверь ссылку или попробуй другую платформу."
        else:
            user_error = f"❌ Ошибка: {error_msg}"
        
        await status_message.edit_text(user_error)
        
        # Очищаем временные файлы в случае ошибки
        for video_path in video_files:
            try:
                if os.path.exists(video_path):
                    os.remove(video_path)
            except:
                pass


def main() -> None:
    """Основная функция запуска бота"""
    # Проверяем доступность FFmpeg при запуске
    if not check_ffmpeg_available():
        logger.error("FFmpeg недоступен! Бот не сможет обрабатывать видео.")
        print("\n" + "="*60)
        print("ОШИБКА: FFmpeg не найден или недоступен!")
        print("="*60)
        print("\nУбедитесь, что FFmpeg установлен и добавлен в PATH.")
        print("Проверьте установку командой: ffmpeg -version")
        print("\nИнструкции по установке FFmpeg:")
        print("Windows: https://www.ffmpeg.org/download.html")
        print("  - Скачайте и распакуйте")
        print("  - Добавьте папку bin в переменную PATH")
        print("="*60 + "\n")
        return
    
    # Создаём приложение
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Регистрируем обработчики
    # Важно: обработчик видео должен быть ПЕРЕД текстовыми сообщениями
    app.add_handler(CommandHandler("start", start))
    # Обрабатываем видео, video_note и документы с видео
    # Используем фильтр для документов с MIME типом video
    video_document_filter = filters.Document.MimeType("video/")
    app.add_handler(MessageHandler(
        filters.VIDEO | filters.VIDEO_NOTE | video_document_filter, 
        handle_video_file
    ))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Добавляем логирование всех входящих сообщений для отладки
    async def log_all_messages(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if update.message:
            logger.info(f"Входящее сообщение: тип={update.message.content_type}, chat_id={update.message.chat_id}, "
                       f"has_text={bool(update.message.text)}, has_video={bool(update.message.video)}, "
                       f"has_document={bool(update.message.document)}")
    
    app.add_handler(MessageHandler(filters.ALL, log_all_messages), group=1)
    
    
    logger.info("Бот запущен и готов к работе!")
    print("Бот запущен! Нажмите Ctrl+C для остановки.")
    
    # Запускаем бота
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()

