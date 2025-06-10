import re
from urllib.parse import urlparse

def validate_url(url: str) -> bool:
    """
    Проверяет валидность URL и поддерживаемые платформы
    
    Args:
        url (str): URL для проверки
        
    Returns:
        bool: True если URL валидный и поддерживается, False в противном случае
    """
    try:
        # Проверяем базовую структуру URL
        result = urlparse(url)
        if not all([result.scheme, result.netloc]):
            return False
        
        # Проверяем поддерживаемые платформы
        supported_domains = [
            'wildberries.ru',
            'www.wildberries.ru',
            'ozon.ru',
            'www.ozon.ru',
            'market.yandex.ru',
            'www.market.yandex.ru'
        ]
        
        return result.netloc in supported_domains
    except Exception:
        return False

def validate_price(price: float) -> bool:
    """
    Проверяет валидность цены
    
    Args:
        price (float): Цена для проверки
        
    Returns:
        bool: True если цена валидная, False в противном случае
    """
    try:
        return isinstance(price, (int, float)) and price > 0
    except Exception:
        return False

def validate_discount(discount: float) -> bool:
    """
    Проверяет валидность скидки
    
    Args:
        discount (float): Скидка для проверки
        
    Returns:
        bool: True если скидка валидная, False в противном случае
    """
    try:
        return isinstance(discount, (int, float)) and 0 <= discount <= 100
    except Exception:
        return False 