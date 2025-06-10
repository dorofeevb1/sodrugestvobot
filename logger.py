import logging
import json
from datetime import datetime
from typing import Dict, Any

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot_activity.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class UserActivityLogger:
    def __init__(self):
        self.log_file = 'user_activity.json'
        self._load_data()

    def _load_data(self) -> Dict[str, Any]:
        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _save_data(self, data: Dict[str, Any]):
        with open(self.log_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

    def log_user_action(self, user_id: int, action: str, additional_data: Dict[str, Any] = None):
        """Логирование действий пользователя"""
        data = self._load_data()
        user_id_str = str(user_id)
        
        if user_id_str not in data:
            data[user_id_str] = {
                'actions': [],
                'first_seen': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'last_seen': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
        
        action_data = {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'action': action
        }
        
        if additional_data:
            action_data.update(additional_data)
            
        data[user_id_str]['actions'].append(action_data)
        data[user_id_str]['last_seen'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        self._save_data(data)
        logger.info(f"User {user_id} performed action: {action}")

    def log_user_info(self, user_id: int, username: str, first_name: str, last_name: str, phone_number: str = None):
        """Логирование информации о пользователе"""
        data = self._load_data()
        user_id_str = str(user_id)
        
        if user_id_str not in data:
            data[user_id_str] = {
                'user_info': {},
                'actions': [],
                'first_seen': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'last_seen': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
        
        user_info = {
            'username': username,
            'first_name': first_name,
            'last_name': last_name,
            'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        if phone_number:
            user_info['phone_number'] = phone_number
        
        data[user_id_str]['user_info'] = user_info
        data[user_id_str]['last_seen'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        self._save_data(data)
        logger.info(f"Updated user info for {user_id}")

    def get_user_stats(self, user_id: int) -> Dict[str, Any]:
        """Получение статистики по пользователю"""
        data = self._load_data()
        return data.get(str(user_id), {})

    def get_all_stats(self) -> Dict[str, Any]:
        """Получение статистики по всем пользователям"""
        return self._load_data()

    def delete_user_data(self, user_id: int):
        """Удаление всех данных пользователя"""
        data = self._load_data()
        user_id_str = str(user_id)
        
        if user_id_str in data:
            del data[user_id_str]
            self._save_data(data)
            logger.info(f"Deleted all data for user {user_id}")

# Создаем глобальный экземпляр логгера
activity_logger = UserActivityLogger() 