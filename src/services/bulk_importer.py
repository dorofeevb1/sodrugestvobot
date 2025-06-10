import logging
from typing import List, Dict
from src.services.database import DatabaseService
from src.services.parser import ParserService
import asyncio
import re

logger = logging.getLogger(__name__)

class BulkImporterService:
    """Сервис для массового импорта товаров"""
    
    def __init__(self):
        self.parser = ParserService()
    
    def _get_platform_from_url(self, url: str) -> str:
        """Определение платформы по URL"""
        if 'wildberries.ru' in url:
            return 'wildberries'
        elif 'ozon.ru' in url:
            return 'ozon'
        elif 'market.yandex.ru' in url:
            return 'market'
        else:
            raise ValueError(f"Неподдерживаемая платформа для URL: {url}")
    
    async def import_from_file(self, telegram_id: int, file_path: str) -> Dict[str, List[str]]:
        """
        Импорт товаров из файла
        
        Args:
            telegram_id (int): ID пользователя в Telegram
            file_path (str): Путь к файлу со ссылками
            
        Returns:
            Dict[str, List[str]]: Результаты импорта
        """
        results = {
            'success': [],
            'errors': []
        }
        
        try:
            # Читаем файл
            with open(file_path, 'r') as file:
                links = [line.strip() for line in file if line.strip()]
            
            # Обрабатываем каждую ссылку
            for link in links:
                try:
                    # Определяем платформу
                    platform = self._get_platform_from_url(link)
                    
                    # Получаем данные о товаре
                    product_data = await self.parser.get_product_data(link, platform)
                    
                    if not product_data:
                        results['errors'].append(f"Не удалось получить данные для {link}")
                        continue
                    
                    # Добавляем товар в базу
                    DatabaseService.add_product(
                        telegram_id=telegram_id,
                        url=link,
                        platform=platform,
                        name=product_data['name'],
                        current_price=product_data['current_price'],
                        original_price=product_data['original_price']
                    )
                    
                    results['success'].append(f"Добавлен товар: {product_data['name']}")
                    
                except Exception as e:
                    logger.error(f"Ошибка при обработке ссылки {link}: {str(e)}")
                    results['errors'].append(f"Ошибка при обработке {link}: {str(e)}")
                
                # Небольшая задержка между запросами
                await asyncio.sleep(1)
            
            return results
            
        except Exception as e:
            logger.error(f"Ошибка при импорте из файла: {str(e)}")
            raise 