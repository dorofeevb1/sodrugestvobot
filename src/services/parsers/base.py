import logging
from abc import ABC, abstractmethod
from typing import Optional
import undetected_chromedriver as uc
from selenium.webdriver.chrome.options import Options

logger = logging.getLogger(__name__)

class BaseParser(ABC):
    """Базовый класс для парсеров"""
    
    def __init__(self):
        self.options = Options()
        self.options.add_argument('--headless')  # Запуск в фоновом режиме
        self.options.add_argument('--no-sandbox')
        self.options.add_argument('--disable-dev-shm-usage')
        self.options.add_argument('--disable-gpu')
        self.options.add_argument('--disable-extensions')
        self.options.add_argument('--disable-infobars')
        self.options.add_argument('--disable-notifications')
        self.options.add_argument('--disable-popup-blocking')
        self.options.add_argument('--disable-blink-features=AutomationControlled')
        self.options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    async def _init_driver(self) -> Optional[uc.Chrome]:
        """
        Инициализация драйвера Chrome
        
        Returns:
            Optional[uc.Chrome]: Экземпляр драйвера или None в случае ошибки
        """
        try:
            driver = uc.Chrome(options=self.options)
            return driver
        except Exception as e:
            logger.error(f"Ошибка при инициализации драйвера: {str(e)}")
            return None
    
    @abstractmethod
    async def get_product_data(self, url: str) -> Optional[dict]:
        """
        Получение данных о товаре
        
        Args:
            url (str): URL товара
            
        Returns:
            Optional[dict]: Данные о товаре или None в случае ошибки
        """
        pass 