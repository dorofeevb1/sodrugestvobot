import logging
from aiogram import Bot
from src.config.config import BOT_TOKEN

logger = logging.getLogger(__name__)

class NotificationService:
    def __init__(self):
        self.bot = Bot(token=BOT_TOKEN)

    async def send_price_change_notification(self, user_id: int, product_name: str, old_price: float, new_price: float):
        """Отправляет уведомление об изменении цены"""
        try:
            price_change = ((new_price - old_price) / old_price) * 100
            change_emoji = "📈" if price_change > 0 else "📉"
            
            message = (
                f"🔔 *Изменение цены*\n\n"
                f"🛍 Товар: {product_name}\n"
                f"💰 Старая цена: {old_price} ₽\n"
                f"💰 Новая цена: {new_price} ₽\n"
                f"{change_emoji} Изменение: {price_change:+.1f}%"
            )
            
            await self.bot.send_message(
                chat_id=user_id,
                text=message,
                parse_mode="Markdown"
            )
            logger.info(f"Отправлено уведомление пользователю {user_id} о изменении цены товара {product_name}")
            
        except Exception as e:
            logger.error(f"Ошибка при отправке уведомления: {str(e)}")

    async def send_error_notification(self, user_id: int, error_message: str):
        """Отправляет уведомление об ошибке"""
        try:
            message = (
                "❌ *Произошла ошибка*\n\n"
                f"{error_message}\n\n"
                "Пожалуйста, попробуйте позже или обратитесь в поддержку."
            )
            
            await self.bot.send_message(
                chat_id=user_id,
                text=message,
                parse_mode="Markdown"
            )
            logger.info(f"Отправлено уведомление об ошибке пользователю {user_id}")
            
        except Exception as e:
            logger.error(f"Ошибка при отправке уведомления об ошибке: {str(e)}")

    async def send_success_notification(self, user_id: int, message: str):
        """Отправляет уведомление об успешном действии"""
        try:
            await self.bot.send_message(
                chat_id=user_id,
                text=f"✅ {message}",
                parse_mode="Markdown"
            )
            logger.info(f"Отправлено уведомление об успехе пользователю {user_id}")
            
        except Exception as e:
            logger.error(f"Ошибка при отправке уведомления об успехе: {str(e)}") 