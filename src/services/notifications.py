from datetime import datetime
from typing import Dict, List
import logging
from src.config.config import NOTIFICATION_THRESHOLD
from collections import deque

logger = logging.getLogger(__name__)

class NotificationService:
    def __init__(self):
        self.notification_queue = deque(maxlen=1000)  # Ограничиваем размер очереди

    def check_price_change(self, product_id: int, old_price: float, new_price: float) -> bool:
        """Проверяет, нужно ли отправить уведомление об изменении цены"""
        if old_price == 0:
            return False
        
        price_change = abs(new_price - old_price) / old_price
        return price_change >= NOTIFICATION_THRESHOLD

    def add_notification(self, user_id: int, product_id: int, 
                        old_price: float, new_price: float, product_name: str):
        """Добавляет уведомление в очередь"""
        notification = {
            'user_id': user_id,
            'product_id': product_id,
            'old_price': old_price,
            'new_price': new_price,
            'product_name': product_name,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        try:
            self.notification_queue.append(notification)
        except Exception as e:
            logger.error(f"Ошибка при добавлении уведомления: {str(e)}")

    def get_pending_notifications(self) -> List[Dict]:
        """Получает все ожидающие уведомления"""
        notifications = []
        while self.notification_queue:
            notifications.append(self.notification_queue.popleft())
        return notifications

    def format_notification_message(self, notification: Dict) -> str:
        """Форматирует сообщение уведомления"""
        price_change = notification['new_price'] - notification['old_price']
        change_percent = (price_change / notification['old_price']) * 100
        
        emoji = "📈" if price_change > 0 else "📉"
        direction = "выросла" if price_change > 0 else "упала"
        
        return (
            f"{emoji} *Изменение цены*\n\n"
            f"Товар: {notification['product_name']}\n"
            f"Цена {direction} на {abs(change_percent):.1f}%\n"
            f"Старая цена: {notification['old_price']}₽\n"
            f"Новая цена: {notification['new_price']}₽"
        ) 