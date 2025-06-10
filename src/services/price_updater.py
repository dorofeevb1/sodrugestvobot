import asyncio
import logging
from datetime import datetime
from sqlalchemy import text
from src.config.config import PRICE_UPDATE_INTERVAL
from src.services.database import DatabaseService, get_db
from src.services.parser import ParserService
from src.services.notification import NotificationService

logger = logging.getLogger(__name__)

class PriceUpdaterService:
    def __init__(self):
        self.parser = ParserService()
        self.notification = NotificationService()
        self._task = None

    async def update_prices(self):
        """Обновление цен всех товаров"""
        try:
            with get_db() as db:
                # Получаем все товары
                products = db.execute(
                    text("SELECT * FROM products")
                ).fetchall()
                
                for product in products:
                    try:
                        # Получаем новую цену
                        new_price = await self.parser.get_price(product.url)
                        
                        if new_price is not None and isinstance(new_price, (int, float)):
                            # Обновляем цену в базе
                            DatabaseService.update_product_price(product.id, new_price)
                            
                            # Проверяем необходимость уведомления
                            if abs(new_price - product.current_price) / product.current_price >= 0.1:  # 10% изменение
                                await self.notification.send_price_change_notification(
                                    product.user_id,
                                    product.name,
                                    product.current_price,
                                    new_price
                                )
                        else:
                            logger.warning(f"Не удалось получить цену для товара {product.id}")
                    except Exception as e:
                        logger.error(f"Ошибка при обновлении цены товара {product.id}: {str(e)}")
                        continue
                        
        except Exception as e:
            logger.error(f"Ошибка при обновлении цен: {str(e)}")

    async def start_price_updates(self):
        """Запуск периодического обновления цен"""
        while True:
            try:
                await self.update_prices()
            except Exception as e:
                logger.error(f"Ошибка при обновлении цен: {str(e)}")
            await asyncio.sleep(PRICE_UPDATE_INTERVAL)

    async def start(self):
        """Запуск сервиса обновления цен"""
        if self._task is None:
            self._task = asyncio.create_task(self.start_price_updates())
            logger.info("Сервис обновления цен запущен")

    async def stop(self):
        """Остановка сервиса обновления цен"""
        if self._task is not None:
            self._task.cancel()
            self._task = None
            logger.info("Сервис обновления цен остановлен") 