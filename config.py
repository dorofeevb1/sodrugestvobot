import os
from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла
load_dotenv()

# Токен бота
BOT_TOKEN = os.getenv('BOT_TOKEN')
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не найден в переменных окружения")

# API ID и Hash для Telethon
API_ID = os.getenv('API_ID')
API_HASH = os.getenv('API_HASH')
if not API_ID or not API_HASH:
    raise ValueError("API_ID или API_HASH не найдены в переменных окружения")

# Директории для хранения данных
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SESSIONS_DIR = os.path.join(BASE_DIR, 'sessions')
DATA_DIR = os.path.join(BASE_DIR, 'data')
LOGS_DIR = os.path.join(BASE_DIR, 'logs')

# Создаем директории, если их нет
os.makedirs(SESSIONS_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)

# Настройки парсера
PARSER_TIMEOUT = 30  # таймаут для запросов в секундах
PARSER_RETRIES = 3   # количество попыток при ошибке
PARSER_DELAY = 1     # задержка между запросами в секундах

# Настройки бота
BOT_ADMIN_IDS = [
    int(id) for id in os.getenv('BOT_ADMIN_IDS', '').split(',')
    if id.strip().isdigit()
] 