"""Модуль для обработки видео: скачивание, нарезка, конвертация в кружочки"""

import os
import subprocess
import asyncio
import logging
import re
import yt_dlp
from pathlib import Path
from typing import List
import config

logger = logging.getLogger(__name__)

# Создаём папку для временных файлов
TEMP_DIR = Path(config.TEMP_VIDEOS_DIR)
TEMP_DIR.mkdir(exist_ok=True)


def get_ffmpeg_command(command: str) -> str:
    """
    Возвращает команду для запуска FFmpeg/ffprobe с учётом настроек из config.
    
    Args:
        command: 'ffmpeg' или 'ffprobe'
        
    Returns:
        Путь к исполняемому файлу или имя команды
    """
    if command == 'ffmpeg':
        return config.FFMPEG_PATH if config.FFMPEG_PATH else 'ffmpeg'
    elif command == 'ffprobe':
        return config.FFPROBE_PATH if config.FFPROBE_PATH else 'ffprobe'
    else:
        return command


def check_ffmpeg_available() -> bool:
    """
    Проверяет доступность FFmpeg и (опционально) ffprobe в системе.

    Возвращает True, если FFmpeg доступен. Отсутствие ffprobe не считается
    критической ошибкой, так как длительность мы умеем получать и через ffmpeg.
    """
    # Проверяем ffmpeg
    try:
        ffmpeg_cmd = get_ffmpeg_command("ffmpeg")
        result = subprocess.run(
            [ffmpeg_cmd, "-version"],
            capture_output=True,
            timeout=5,
        )
        if result.returncode != 0:
            logger.error("FFmpeg найден, но возвращает ошибку")
            return False
    except FileNotFoundError:
        logger.error(
            "FFmpeg не найден. Проверьте установку и PATH, "
            "или укажите путь FFMPEG_PATH в config.py"
        )
        return False
    except subprocess.TimeoutExpired:
        logger.error("Таймаут при проверке FFmpeg")
        return False
    except Exception as e:
        logger.error(f"Ошибка при проверке FFmpeg: {e}")
        return False

    # Пробуем проверить ffprobe, но отсутствие не считаем фатальной ошибкой
    try:
        ffprobe_cmd = get_ffmpeg_command("ffprobe")
        result = subprocess.run(
            [ffprobe_cmd, "-version"],
            capture_output=True,
            timeout=5,
        )
        if result.returncode != 0:
            logger.warning("ffprobe найден, но возвращает ошибку, будет использован ffmpeg")
        else:
            logger.info(
                f"FFmpeg и ffprobe доступны (ffmpeg: {ffmpeg_cmd}, ffprobe: {ffprobe_cmd})"
            )
    except FileNotFoundError:
        logger.warning("ffprobe не найден, для длительности будет использован ffmpeg")
    except Exception as e:
        logger.warning(f"Ошибка при проверке ffprobe: {e}")

    return True


async def download_video(url: str) -> str:
    """
    Асинхронно скачивает видео по ссылке через yt-dlp.
    
    Args:
        url: Ссылка на видео (YouTube, TikTok, Instagram и т.д.)
        
    Returns:
        Путь к скачанному видеофайлу
        
    Raises:
        Exception: Если не удалось скачать видео
    """
    output_path = TEMP_DIR / "source_video.%(ext)s"
    
    ydl_opts = {
        'format': 'best[ext=mp4]/best',
        'outtmpl': str(output_path),
        'quiet': True,
        'no_warnings': True,
    }
    
    # yt-dlp не поддерживает async напрямую, запускаем в executor
    loop = asyncio.get_event_loop()
    
    def download():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
    
    await loop.run_in_executor(None, download)
    
    # Находим скачанный файл
    for ext in ['mp4', 'webm', 'mkv', 'm4a']:
        video_path = TEMP_DIR / f"source_video.{ext}"
        if video_path.exists():
            return str(video_path)
    
    raise Exception("Не удалось найти скачанный файл")


async def get_video_duration(video_path: str) -> float:
    """
    Получает длительность видео в секундах через ffprobe или ffmpeg.
    
    Args:
        video_path: Путь к видеофайлу
        
    Returns:
        Длительность в секундах (float)
        
    Raises:
        Exception: Если не удалось получить длительность
    """
    # Сначала пробуем ffprobe
    ffprobe_cmd = get_ffmpeg_command('ffprobe')
    cmd = [
        ffprobe_cmd, '-v', 'error', '-show_entries',
        'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1',
        video_path
    ]
    
    loop = asyncio.get_event_loop()
    
    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        
        if process.returncode == 0:
            duration_str = stdout.decode('utf-8', errors='ignore').strip()
            if duration_str:
                return float(duration_str)
    except FileNotFoundError:
        # Если ffprobe не найден, пробуем использовать ffmpeg
        logger.warning("ffprobe не найден, используем ffmpeg для получения длительности")
        pass
    except Exception:
        # Если ошибка, пробуем ffmpeg
        pass
    
    # Альтернативный способ через ffmpeg
    try:
        ffmpeg_cmd = get_ffmpeg_command('ffmpeg')
        cmd = [
            ffmpeg_cmd, '-i', video_path, '-f', 'null', '-'
        ]
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        
        # Парсим длительность из вывода ffmpeg
        error_output = stderr.decode('utf-8', errors='ignore')
        # Ищем строку вида "Duration: 00:01:23.45"
        duration_match = re.search(r'Duration:\s*(\d+):(\d+):(\d+\.?\d*)', error_output)
        if duration_match:
            hours = int(duration_match.group(1))
            minutes = int(duration_match.group(2))
            seconds = float(duration_match.group(3))
            total_seconds = hours * 3600 + minutes * 60 + seconds
            return total_seconds
        
        raise Exception("Не удалось найти длительность в выводе ffmpeg")
    except FileNotFoundError as e:
        raise Exception(f"FFmpeg не найден. Убедитесь, что FFmpeg установлен и доступен в PATH. Ошибка: {e}")
    except Exception as e:
        raise Exception(f"Ошибка при получении длительности видео: {e}")


async def optimize_video_size(video_path: str, max_size: int = config.MAX_FILE_SIZE) -> str:
    """
    Оптимизирует размер видеофайла, если он превышает лимит.
    
    Args:
        video_path: Путь к видеофайлу
        max_size: Максимальный размер в байтах
        
    Returns:
        Путь к оптимизированному файлу (может быть тот же, если оптимизация не нужна)
    """
    file_size = os.path.getsize(video_path)
    
    if file_size <= max_size:
        return video_path
    
    # Пробуем уменьшить разрешение
    optimized_path = video_path.replace('.mp4', '_optimized.mp4')
    size = config.VIDEO_SIZE
    
    # Уменьшаем разрешение пока файл слишком большой
    while file_size > max_size and size >= 256:
        ffmpeg_cmd = get_ffmpeg_command('ffmpeg')
        cmd = [
            ffmpeg_cmd, '-i', video_path,
            '-vf', f'scale={size}:{size}:force_original_aspect_ratio=decrease,'
                   f'pad={size}:{size}:(ow-iw)/2:(oh-ih)/2:color=black',
            '-c:v', config.FFMPEG_VIDEO_CODEC,
            '-preset', config.FFMPEG_PRESET,
            '-crf', '28',  # Увеличиваем CRF для меньшего размера
            '-c:a', config.FFMPEG_AUDIO_CODEC,
            '-b:a', '96k',  # Уменьшаем битрейт аудио
            '-movflags', '+faststart',
            '-y',
            optimized_path
        ]
        
        loop = asyncio.get_event_loop()
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        await process.communicate()
        
        if process.returncode == 0 and os.path.exists(optimized_path):
            file_size = os.path.getsize(optimized_path)
            if file_size <= max_size:
                # Удаляем оригинал, если он отличается
                if optimized_path != video_path:
                    try:
                        os.remove(video_path)
                    except:
                        pass
                return optimized_path
            else:
                # Пробуем ещё меньшее разрешение
                size -= 64
                video_path = optimized_path
        else:
            break
    
    # Если всё ещё слишком большой, возвращаем что есть
    return optimized_path if os.path.exists(optimized_path) else video_path


async def cut_video_to_circles(video_path: str, segment_duration: int = config.DEFAULT_SEGMENT_DURATION) -> List[str]:
    """
    Нарезает видео на отрезки и преобразует в квадратный формат для кружочек.
    
    Args:
        video_path: Путь к исходному видео
        segment_duration: Длительность каждого отрезка в секундах
        
    Returns:
        Список путей к обработанным файлам
        
    Raises:
        Exception: Если не удалось обработать видео
    """
    # Проверяем и ограничиваем длительность отрезка
    segment_duration = max(config.MIN_SEGMENT_DURATION, 
                          min(config.MAX_SEGMENT_DURATION, segment_duration))
    
    duration = await get_video_duration(video_path)
    output_files = []
    size = config.VIDEO_SIZE
    
    start_time = 0.0
    segment_num = 0
    
    while start_time < duration:
        end_time = min(start_time + segment_duration, duration)
        actual_duration = end_time - start_time
        
        # Пропускаем слишком короткие отрезки (< 1 секунды)
        if actual_duration < 1.0:
            break
        
        output_path = TEMP_DIR / f"circle_{segment_num}.mp4"
        
        # FFmpeg команда для обработки одного отрезка
        ffmpeg_cmd = get_ffmpeg_command('ffmpeg')
        cmd = [
            ffmpeg_cmd, '-i', video_path,
            '-ss', str(start_time),
            '-t', str(actual_duration),
            '-vf', f'scale={size}:{size}:force_original_aspect_ratio=decrease,'
                   f'pad={size}:{size}:(ow-iw)/2:(oh-ih)/2:color=black',
            '-c:v', config.FFMPEG_VIDEO_CODEC,
            '-preset', config.FFMPEG_PRESET,
            '-crf', str(config.FFMPEG_CRF),
            '-c:a', config.FFMPEG_AUDIO_CODEC,
            '-b:a', config.FFMPEG_AUDIO_BITRATE,
            '-movflags', '+faststart',
            '-y',  # Перезаписать если существует
            str(output_path)
        ]
        
        loop = asyncio.get_event_loop()
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                error_msg = stderr.decode('utf-8', errors='ignore') if stderr else "Неизвестная ошибка"
                logger.error(f"Ошибка обработки отрезка {segment_num} (код {process.returncode}): {error_msg}")
                # Продолжаем с другими отрезками, даже если один не удался
            elif os.path.exists(output_path):
                # Оптимизируем размер файла
                optimized_path = await optimize_video_size(str(output_path))
                output_files.append(optimized_path)
            else:
                logger.warning(f"Файл {output_path} не был создан")
        except FileNotFoundError as e:
            logger.error(f"FFmpeg не найден при обработке отрезка {segment_num}: {e}")
            raise Exception("FFmpeg не найден. Убедитесь, что FFmpeg установлен и доступен в PATH")
        except Exception as e:
            logger.error(f"Неожиданная ошибка при обработке отрезка {segment_num}: {e}")
            raise
        
        start_time = end_time
        segment_num += 1
    
    if not output_files:
        raise Exception("Не удалось создать ни одного отрезка")
    
    return output_files


async def process_video_to_circles(url: str, segment_duration: int = config.DEFAULT_SEGMENT_DURATION) -> List[str]:
    """
    Основная функция: скачивает видео и обрабатывает его в кружочки.
    
    Args:
        url: Ссылка на видео
        segment_duration: Длительность каждого отрезка в секундах
        
    Returns:
        Список путей к обработанным файлам
        
    Raises:
        Exception: Если не удалось обработать видео
    """
    video_path = None
    try:
        # Скачиваем видео
        video_path = await download_video(url)
        
        # Нарезаем на кружочки
        circles = await cut_video_to_circles(video_path, segment_duration)
        
        return circles
    except Exception as e:
        raise Exception(f"Ошибка обработки видео: {str(e)}")
    finally:
        # Удаляем исходное видео
        if video_path and os.path.exists(video_path):
            try:
                os.remove(video_path)
            except:
                pass

