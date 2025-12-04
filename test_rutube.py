"""Тестовый скрипт для проверки обработки Rutube видео"""

import asyncio
import logging
from video_processor import process_video_to_circles, check_ffmpeg_available

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_rutube():
    """Тестирует обработку видео с Rutube"""
    url = "https://rutube.ru/video/570283471933912da8a93194ac8d30c0/?r=wd"
    
    print("=" * 60)
    print("Тест обработки Rutube видео")
    print("=" * 60)
    
    # Проверяем FFmpeg
    print("\n1. Проверка FFmpeg...")
    if not check_ffmpeg_available():
        print("❌ FFmpeg недоступен!")
        return
    print("✅ FFmpeg доступен")
    
    # Тестируем обработку
    print(f"\n2. Обработка видео: {url}")
    try:
        video_files = await process_video_to_circles(url, segment_duration=10)
        print(f"✅ Успешно создано {len(video_files)} кружочков:")
        for i, path in enumerate(video_files, 1):
            import os
            size = os.path.getsize(path) / (1024 * 1024)  # МБ
            print(f"   {i}. {path} ({size:.2f} МБ)")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    asyncio.run(test_rutube())

