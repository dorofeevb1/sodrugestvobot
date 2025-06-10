import os
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Токен бота
BOT_TOKEN = os.getenv('BOT_TOKEN')
if not BOT_TOKEN:
    raise ValueError("Не указан токен бота (BOT_TOKEN)")

# Настройки базы данных
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///products.db')

# Настройки парсинга
PARSING_TIMEOUT = int(os.getenv('PARSING_TIMEOUT', '30'))  # секунды
MAX_RETRIES = int(os.getenv('MAX_RETRIES', '3'))
RETRY_DELAY = int(os.getenv('RETRY_DELAY', '5'))  # секунды

# Настройки логирования
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

def validate_config():
    """Проверяет корректность конфигурации"""
    if not BOT_TOKEN:
        raise ValueError("Не указан токен бота (BOT_TOKEN)")
    
    if not DATABASE_URL:
        raise ValueError("Не указан URL базы данных (DATABASE_URL)")
    
    if PARSING_TIMEOUT < 1:
        raise ValueError("Таймаут парсинга должен быть положительным числом")
    
    if MAX_RETRIES < 1:
        raise ValueError("Количество попыток должно быть положительным числом")
    
    if RETRY_DELAY < 1:
        raise ValueError("Задержка между попытками должна быть положительным числом")
    
    return True

# Настройки Redis
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

# Настройки обновления цен
PRICE_UPDATE_INTERVAL = int(os.getenv('PRICE_UPDATE_INTERVAL', '3600'))  # 1 час

# Настройки уведомлений
NOTIFICATION_THRESHOLD = float(os.getenv('NOTIFICATION_THRESHOLD', '0.1'))  # 10% изменения цены

# Проверяем конфигурацию при импорте
validate_config() 