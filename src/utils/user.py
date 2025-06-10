import logging
from src.services.database import DatabaseService

logger = logging.getLogger(__name__)

async def ensure_user_exists(user_id: int, username: str = None) -> bool:
    """
    Проверяет существование пользователя и создает его при необходимости
    
    Args:
        user_id: ID пользователя в Telegram
        username: Имя пользователя в Telegram
        
    Returns:
        bool: True если пользователь существует или был создан, False в случае ошибки
    """
    try:
        # Проверяем существование пользователя
        user = DatabaseService.get_user(user_id)
        if user:
            return True
            
        # Создаем нового пользователя
        DatabaseService.add_user(user_id, username)
        return True
        
    except Exception as e:
        logger.error(f"Ошибка при проверке/создании пользователя: {str(e)}")
        return False 