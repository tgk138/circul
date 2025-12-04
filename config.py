"""Конфигурация бота"""

# Размер видео для кружочков (Telegram video_note)
VIDEO_SIZE = 640  # 640x640 пикселей

# Длительность отрезков по умолчанию (секунды)
DEFAULT_SEGMENT_DURATION = 10

# Минимальная и максимальная длительность отрезков
MIN_SEGMENT_DURATION = 5
MAX_SEGMENT_DURATION = 15

# Максимальный размер файла для Telegram video_note (байты)
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 МБ

# Настройки FFmpeg
FFMPEG_VIDEO_CODEC = "libx264"
FFMPEG_AUDIO_CODEC = "aac"
FFMPEG_PRESET = "fast"
FFMPEG_CRF = 23  # Качество (18-28, меньше = лучше качество, больше размер)
FFMPEG_AUDIO_BITRATE = "128k"

# Путь к временной папке
TEMP_VIDEOS_DIR = "temp_videos"

# Пути к FFmpeg (если не в PATH, укажите полные пути)
# Оставьте None для автоматического поиска в PATH
FFMPEG_PATH = r"C:\Program Files\ImageMagick-7.0.10-Q16-HDRI\ffmpeg.exe"  # Полный путь к ffmpeg
FFPROBE_PATH = None  # ffprobe не найден, будет использован ffmpeg для получения длительности

# Режим обработки видео для кружочков
# "crop" - обрезать до квадрата (без черных полей)
# "pad" - добавить черные поля (старый режим)
VIDEO_CROP_MODE = "crop"  # По умолчанию обрезка

