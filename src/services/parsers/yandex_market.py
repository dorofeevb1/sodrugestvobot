import logging
from bs4 import BeautifulSoup
import aiohttp

logger = logging.getLogger(__name__)

class YandexMarketParser:
    """Парсер для Яндекс.Маркета"""
    
    async def parse_product(self, url: str) -> dict:
        """
        Парсинг данных о товаре с Яндекс.Маркета
        
        Args:
            url (str): URL товара
            
        Returns:
            dict: Данные о товаре
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        raise ValueError(f"Ошибка при получении страницы: {response.status}")
                    
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Получаем название товара
                    name = soup.find('h1').text.strip()
                    
                    # Получаем текущую цену
                    current_price = float(soup.find('span', {'data-auto': 'price'}).text.strip().replace(' ', '').replace('₽', ''))
                    
                    # Получаем оригинальную цену
                    original_price_elem = soup.find('span', {'data-auto': 'oldPrice'})
                    original_price = float(original_price_elem.text.strip().replace(' ', '').replace('₽', '')) if original_price_elem else current_price
                    
                    # Вычисляем скидку
                    discount = round((1 - current_price / original_price) * 100, 2) if original_price > current_price else 0
                    
                    return {
                        'name': name,
                        'current_price': current_price,
                        'original_price': original_price,
                        'discount': discount
                    }
        except Exception as e:
            logger.error(f"Ошибка при парсинге товара с Яндекс.Маркета: {str(e)}")
            raise 