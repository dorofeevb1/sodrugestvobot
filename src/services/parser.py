import aiohttp
import asyncio
from bs4 import BeautifulSoup
from typing import Dict, Optional
import logging
import json
import random
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import os
from src.config.config import PARSING_TIMEOUT, MAX_RETRIES, RETRY_DELAY
import re
from urllib.parse import urlparse
from src.services.parsers.ozon import OzonParser
from src.services.parsers.wildberries import WildberriesParser
from src.services.parsers.yandex_market import YandexMarketParser
from companies_data import get_company_data

logger = logging.getLogger(__name__)

# Список реалистичных User-Agent'ов
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3.1 Safari/605.1.15',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36 Edg/137.0.0.0'
]

class ParserService:
    """Сервис для парсинга товаров"""
    
    def __init__(self):
        """Инициализация парсера"""
        self.parsers = {
            'ozon': OzonParser(),
            'wildberries': WildberriesParser(),
            'yandex_market': YandexMarketParser()
        }
        self.session = None
        self.driver = None
        self.headers = {
            'User-Agent': random.choice(USER_AGENTS)
        }

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(headers=self.headers)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
        if self.driver:
            self.driver.quit()

    def _init_driver(self):
        """Инициализация драйвера Chrome"""
        if self.driver is None:
            try:
                options = uc.ChromeOptions()
                
                # Базовые настройки
                options.add_argument('--no-sandbox')
                options.add_argument('--disable-dev-shm-usage')
                options.add_argument('--disable-gpu')
                options.add_argument('--disable-infobars')
                options.add_argument('--disable-notifications')
                options.add_argument('--disable-popup-blocking')
                options.add_argument('--disable-blink-features=AutomationControlled')
                
                # Установка User-Agent
                user_agent = random.choice(USER_AGENTS)
                options.add_argument(f'user-agent={user_agent}')
                
                # Дополнительные настройки для обхода защиты
                options.add_argument('--disable-blink-features')
                options.add_argument('--disable-extensions')
                options.add_argument('--disable-plugins-discovery')
                options.add_argument('--disable-plugins')
                options.add_argument('--disable-web-security')
                options.add_argument('--ignore-certificate-errors')
                
                # Настройки для эмуляции реального браузера
                options.add_argument('--window-size=1920,1080')
                options.add_argument('--start-maximized')
                
                # Создание директории для профиля Chrome
                profile_dir = os.path.join(os.getcwd(), 'chrome_profile')
                if not os.path.exists(profile_dir):
                    os.makedirs(profile_dir)
                options.add_argument(f'--user-data-dir={profile_dir}')
                
                # Инициализация драйвера
                self.driver = uc.Chrome(
                    options=options,
                    browser_executable_path='/usr/bin/chromium',
                    suppress_welcome=True,
                    use_subprocess=True
                )
                
                # Установка таймаутов
                self.driver.set_page_load_timeout(30)
                self.driver.implicitly_wait(10)
                
                # Установка размера окна
                self.driver.set_window_size(1920, 1080)
                
            except Exception as e:
                logger.error(f"Ошибка при инициализации драйвера: {str(e)}")
                if self.driver:
                    self.driver.quit()
                self.driver = None
                raise

    def _clean_price(self, price_str: str) -> float:
        """Очистка строки цены от неразрывных пробелов и других символов"""
        # Заменяем неразрывные пробелы на обычные
        price_str = price_str.replace('\u2009', ' ').replace('\u00A0', ' ')
        # Удаляем все символы кроме цифр, точки и запятой
        price_str = re.sub(r'[^\d.,]', '', price_str)
        # Заменяем запятую на точку
        price_str = price_str.replace(',', '.')
        try:
            return float(price_str)
        except ValueError as e:
            logger.error(f"Ошибка при преобразовании цены '{price_str}': {str(e)}")
            raise

    def _get_platform(self, url: str) -> str:
        """Определение платформы по URL"""
        domain = urlparse(url).netloc
        if 'wildberries.ru' in domain:
            return 'Wildberries'
        elif 'ozon.ru' in domain:
            return 'Ozon'
        elif 'market.yandex.ru' in domain:
            return 'Market'
        else:
            raise ValueError(f"Неподдерживаемая платформа: {domain}")

    async def get_product_data(self, url: str, platform: str) -> dict:
        """
        Получение данных о товаре
        
        Args:
            url (str): URL товара
            platform (str): Платформа (ozon, wildberries, yandex_market)
            
        Returns:
            dict: Данные о товаре
        """
        try:
            # Получаем данные о товаре используя существующий парсер
            product_data = get_company_data(url)
            
            if not product_data:
                raise ValueError("Не удалось получить данные о товаре")
            
            return {
                'name': product_data['name'],
                'current_price': product_data['price'],
                'original_price': product_data.get('original_price', product_data['price']),
                'discount': product_data.get('discount', 0)
            }
        except Exception as e:
            logger.error(f"Ошибка при парсинге товара: {str(e)}")
            raise

    async def update_prices(self) -> None:
        """Обновление цен всех товаров"""
        try:
            # TODO: Реализовать обновление цен
            pass
        except Exception as e:
            logger.error(f"Ошибка при обновлении цен: {str(e)}")
            raise

    async def parse_ozon(self, url: str) -> Optional[Dict]:
        """Парсинг товара с Ozon"""
        try:
            self._init_driver()
            self.driver.get(url)
            await asyncio.sleep(random.uniform(2, 3))
            
            data = {
                'platform': 'Ozon',
                'name': '',
                'current_price': 0,
                'original_price': 0
            }
            
            try:
                # Ожидание и извлечение названия товара
                name_elem = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, '/html/body/div[1]/div/div[1]/div[3]/div[3]/div[1]/div[1]/div[2]/div/div/div/div[1]/h1'))
                )
                if name_elem:
                    data['name'] = name_elem.text.strip()
                    logger.info(f"Название товара: {data['name']}")
                
                # Ожидание и извлечение цены со скидкой
                price_discount_elem = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, '/html/body/div[1]/div/div[1]/div[3]/div[3]/div[2]/div/div/div[1]/div[2]/div/div[1]/div/div/div[1]/div[1]/button/span/div/div[1]/div/div/span'))
                )
                if price_discount_elem:
                    price_text = price_discount_elem.text.strip()
                    data['current_price'] = self._clean_price(price_text)
                    logger.info(f"Цена со скидкой: {data['current_price']}")
                
                # Ожидание и извлечение цены без скидки
                try:
                    price_no_discount_elem = WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.XPATH, '/html/body/div[1]/div/div[1]/div[3]/div[3]/div[2]/div/div/div[1]/div[2]/div/div[1]/div/div/div[1]/div[2]/div/div[1]/span'))
                    )
                    if price_no_discount_elem:
                        price_text = price_no_discount_elem.text.strip()
                        data['original_price'] = self._clean_price(price_text)
                        logger.info(f"Цена без скидки: {data['original_price']}")
                except TimeoutException:
                    data['original_price'] = data['current_price']
                    logger.info("Цена без скидки не найдена, используем текущую цену")
                
            except Exception as e:
                logger.error(f"Ошибка при извлечении данных товара: {str(e)}")
                return None
            
            return data
            
        except Exception as e:
            logger.error(f"Ошибка при парсинге Ozon {url}: {str(e)}")
            return None
        finally:
            if self.driver:
                self.driver.quit()
                self.driver = None

    async def parse_wildberries(self, url: str) -> Optional[Dict]:
        """Парсинг товара с Wildberries"""
        try:
            self._init_driver()
            self.driver.get(url)
            await asyncio.sleep(random.uniform(2, 3))
            
            data = {
                'platform': 'Wildberries',
                'name': '',
                'current_price': 0,
                'original_price': 0
            }
            
            try:
                # Ожидание и извлечение названия товара
                name_elem = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CLASS_NAME, 'product-page__header'))
                )
                if name_elem:
                    data['name'] = name_elem.text.strip()
                    logger.info(f"Название товара: {data['name']}")
                
                # Ожидание и извлечение цены со скидкой
                price_discount_elem = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CLASS_NAME, 'price-block__final-price'))
                )
                if price_discount_elem:
                    price_text = price_discount_elem.text.strip()
                    data['current_price'] = self._clean_price(price_text)
                    logger.info(f"Цена со скидкой: {data['current_price']}")
                
                # Ожидание и извлечение цены без скидки
                try:
                    price_no_discount_elem = WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.CLASS_NAME, 'price-block__old-price'))
                    )
                    if price_no_discount_elem:
                        price_text = price_no_discount_elem.text.strip()
                        data['original_price'] = self._clean_price(price_text)
                        logger.info(f"Цена без скидки: {data['original_price']}")
                except TimeoutException:
                    data['original_price'] = data['current_price']
                    logger.info("Цена без скидки не найдена, используем текущую цену")
                
            except Exception as e:
                logger.error(f"Ошибка при извлечении данных товара: {str(e)}")
                return None
            
            return data
            
        except Exception as e:
            logger.error(f"Ошибка при парсинге Wildberries {url}: {str(e)}")
            return None
        finally:
            if self.driver:
                self.driver.quit()
                self.driver = None

    async def parse_market(self, url: str) -> Optional[Dict]:
        """Парсинг товара с Яндекс.Маркета"""
        try:
            self._init_driver()
            self.driver.get(url)
            await asyncio.sleep(random.uniform(2, 3))
            
            data = {
                'platform': 'Market',
                'name': '',
                'current_price': 0,
                'original_price': 0
            }
            
            try:
                # Ожидание и извлечение названия товара
                name_elem = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CLASS_NAME, 'cia-cs'))
                )
                if name_elem:
                    data['name'] = name_elem.text.strip()
                    logger.info(f"Название товара: {data['name']}")
                
                # Ожидание и извлечение цены со скидкой
                price_discount_elem = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CLASS_NAME, 'cia-cs'))
                )
                if price_discount_elem:
                    price_text = price_discount_elem.text.strip()
                    data['current_price'] = self._clean_price(price_text)
                    logger.info(f"Цена со скидкой: {data['current_price']}")
                
                # Ожидание и извлечение цены без скидки
                try:
                    price_no_discount_elem = WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.CLASS_NAME, 'cia-cs'))
                    )
                    if price_no_discount_elem:
                        price_text = price_no_discount_elem.text.strip()
                        data['original_price'] = self._clean_price(price_text)
                        logger.info(f"Цена без скидки: {data['original_price']}")
                except TimeoutException:
                    data['original_price'] = data['current_price']
                    logger.info("Цена без скидки не найдена, используем текущую цену")
                
            except Exception as e:
                logger.error(f"Ошибка при извлечении данных товара: {str(e)}")
                return None
            
            return data
            
        except Exception as e:
            logger.error(f"Ошибка при парсинге Яндекс.Маркет {url}: {str(e)}")
            return None
        finally:
            if self.driver:
                self.driver.quit()
                self.driver = None 