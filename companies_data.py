import pandas as pd
import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
import time
import random
from typing import List, Dict, Optional
import logging
import re
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import os

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('companies_parser.log'),
        logging.StreamHandler()
    ]
)

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

# Создаем глобальный экземпляр парсера
parser = None

def get_company_data(url: str) -> Dict[str, any]:
    """
    Получение данных о товаре с различных платформ
    
    Args:
        url (str): URL товара
        
    Returns:
        Dict[str, any]: Данные о товаре
    """
    global parser
    if parser is None:
        parser = CompanyDataParser()
    
    try:
        # Определяем платформу по URL
        if 'ozon.ru' in url:
            data = parser.parse_ozon_page(url)
        elif 'wildberries.ru' in url:
            data = parser.parse_wb_page(url)
        else:
            raise ValueError(f"Неподдерживаемая платформа: {url}")
        
        if not data:
            raise ValueError("Не удалось получить данные о товаре")
        
        # Преобразуем цены в числа, удаляя все нецифровые символы кроме точки
        def parse_price(price_str: str) -> float:
            if not price_str:
                return 0
            # Удаляем все символы кроме цифр
            digits = ''.join(filter(str.isdigit, price_str))
            return float(digits) if digits else 0
        
        current_price = parse_price(data['price_with_discount'])
        original_price = parse_price(data['price_without_discount']) or current_price
        
        # Вычисляем скидку
        discount = round((1 - current_price / original_price) * 100, 2) if original_price > current_price else 0
        
        return {
            'name': data['product_name'],
            'price': current_price,
            'original_price': original_price,
            'discount': discount
        }
    except Exception as e:
        logging.error(f"Ошибка при получении данных о товаре: {str(e)}")
        raise

class CompanyDataParser:
    def __init__(self):
        self.session = requests.Session()
        self.driver = None
        
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
                    browser_executable_path='/usr/bin/chromium',  # путь к Chromium
                    suppress_welcome=True,  # Отключение приветственного экрана
                    use_subprocess=True  # Использование подпроцесса
                )
                
                # Установка таймаутов
                self.driver.set_page_load_timeout(30)
                self.driver.implicitly_wait(10)
                
                # Установка размера окна
                self.driver.set_window_size(1920, 1080)
                
            except Exception as e:
                logging.error(f"Ошибка при инициализации драйвера: {str(e)}")
                if self.driver:
                    self.driver.quit()
                self.driver = None
                raise
            
    def _close_driver(self):
        """Закрытие драйвера Chrome"""
        if self.driver:
            try:
                self.driver.quit()
            except Exception as e:
                logging.error(f"Ошибка при закрытии драйвера: {str(e)}")
            finally:
                self.driver = None

    def _get_headers(self) -> Dict[str, str]:
        """Генерирует случайные заголовки для запроса"""
        return {
            'User-Agent': random.choice(USER_AGENTS),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
            'DNT': '1',
            'Sec-Ch-Ua': '"Chromium";v="137", "Not(A:Brand";v="24", "Google Chrome";v="137"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"Windows"'
        }
    
    def _make_request(self, url: str, max_retries: int = 3) -> Optional[str]:
        """Выполняет HTTP запрос с повторными попытками"""
        for attempt in range(max_retries):
            try:
                # Случайная задержка перед запросом
                time.sleep(random.uniform(3, 7))
                response = self.session.get(url, headers=self._get_headers(), timeout=15)
                response.raise_for_status()
                return response.text
            except requests.RequestException as e:
                logging.error(f"Ошибка при запросе {url}: {str(e)}")
                if attempt < max_retries - 1:
                    # Увеличенная задержка между повторными попытками
                    time.sleep(random.uniform(5, 10))
                continue
        return None

    def parse_ozon_page(self, url: str) -> Dict[str, str]:
        """Парсинг страницы товара на Ozon"""
        try:
            self._init_driver()
            self.driver.get(url)
            time.sleep(random.uniform(2, 3))  # Увеличиваем начальную задержку
            
            data = {
                'url': url,
                'platform': 'Ozon',
                'product_name': '',
                'price_with_discount': '',
                'price_without_discount': ''
            }
            
            try:
                # Ожидание и извлечение названия товара
                try:
                    name_elem = WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.XPATH, '/html/body/div[1]/div/div[1]/div[3]/div[3]/div[1]/div[1]/div[2]/div/div/div/div[1]/h1'))
                    )
                    if name_elem:
                        data['product_name'] = name_elem.text.strip()
                        logging.info(f"Название товара: {data['product_name']}")
                except Exception as e:
                    logging.error(f"Не удалось получить название товара: {str(e)}")
                
                # Ожидание и извлечение цены со скидкой
                try:
                    price_discount_elem = WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.XPATH, '/html/body/div[1]/div/div[1]/div[3]/div[3]/div[2]/div/div/div[1]/div[2]/div/div[1]/div/div/div[1]/div[1]/button/span/div/div[1]/div/div/span'))
                    )
                    if price_discount_elem:
                        data['price_with_discount'] = price_discount_elem.text.strip()
                        logging.info(f"Цена со скидкой: {data['price_with_discount']}")
                except Exception as e:
                    logging.debug(f"Не удалось получить цену со скидкой: {str(e)}")
                
                # Ожидание и извлечение цены без скидки
                try:
                    price_no_discount_elem = WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.XPATH, '/html/body/div[1]/div/div[1]/div[3]/div[3]/div[2]/div/div/div[1]/div[2]/div/div[1]/div/div/div[1]/div[2]/div/div[1]/span'))
                    )
                    if price_no_discount_elem:
                        data['price_without_discount'] = price_no_discount_elem.text.strip()
                        logging.info(f"Цена без скидки: {data['price_without_discount']}")
                except Exception as e:
                    logging.debug(f"Не удалось получить цену без скидки: {str(e)}")
                
            except Exception as e:
                logging.error(f"Ошибка при извлечении данных товара: {str(e)}")
            
            return data
        except Exception as e:
            logging.error(f"Ошибка при парсинге страницы Ozon: {str(e)}")
            raise
        finally:
            self._close_driver()

    def parse_wb_page(self, url: str) -> Dict[str, str]:
        """Парсинг страницы товара на Wildberries"""
        try:
            self._init_driver()
            self.driver.get(url)
            time.sleep(random.uniform(2, 3))  # Увеличиваем начальную задержку
            
            data = {
                'url': url,
                'platform': 'Wildberries',
                'product_name': '',
                'price_with_discount': '',
                'price_without_discount': ''
            }
            
            try:
                # Ожидание и извлечение названия товара
                try:
                    name_elem = WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.CLASS_NAME, 'product-page__header'))
                    )
                    if name_elem:
                        data['product_name'] = name_elem.text.strip()
                        logging.info(f"Название товара: {data['product_name']}")
                except Exception as e:
                    logging.error(f"Не удалось получить название товара: {str(e)}")
                
                # Ожидание и извлечение цены со скидкой
                try:
                    price_discount_elem = WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.XPATH, '/html/body/div[1]/main/div[2]/div[2]/div[3]/div/div[3]/div[13]/div/div[1]/div[1]/div/div/div/p/span/span'))
                    )
                    if price_discount_elem:
                        data['price_with_discount'] = price_discount_elem.text.strip()
                        logging.info(f"Цена со скидкой: {data['price_with_discount']}")
                except Exception as e:
                    logging.debug(f"Не удалось получить цену со скидкой: {str(e)}")
                
                # Ожидание и извлечение цены без скидки
                try:
                    price_no_discount_elem = WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.XPATH, '/html/body/div[1]/main/div[2]/div[2]/div[3]/div/div[3]/div[13]/div/div[1]/div[1]/div/div/div/p/span/ins'))
                    )
                    if price_no_discount_elem:
                        data['price_without_discount'] = price_no_discount_elem.text.strip()
                        logging.info(f"Цена без скидки: {data['price_without_discount']}")
                except Exception as e:
                    logging.debug(f"Не удалось получить цену без скидки: {str(e)}")
                
            except Exception as e:
                logging.error(f"Ошибка при извлечении данных товара: {str(e)}")
            
            return data
            
        except Exception as e:
            logging.error(f"Ошибка при парсинге страницы Wildberries {url}: {str(e)}")
            return data
        finally:
            self._close_driver()

    def process_excel_data(self, excel_path: str) -> pd.DataFrame:
        """Обрабатывает данные из Excel файла"""
        # Чтение Excel файла
        df = pd.read_excel(excel_path)
        results = []
        
        # Обработка каждой строки
        for _, row in df.iterrows():
            company_data = {
                'Юр. лицо': row['Юр. лицо'],
                'Название магазина Ozon': row['Название магазина Ozon'],
                'Название магазина Wb': row['Название магазина Wb']
            }
            
            # Парсинг Ozon
            if pd.notna(row['Ссылка']):
                ozon_data = self.parse_ozon_page(row['Ссылка'])
                # Добавляем названия товаров в отдельные колонки
                if 'product_names' in ozon_data:
                    for i, name in enumerate(ozon_data['product_names'], 1):
                        company_data[f'Ozon_Товар_{i}'] = name
                    del ozon_data['product_names']  # Удаляем список из данных
                company_data.update({f'Ozon_{k}': v for k, v in ozon_data.items()})
                # Увеличенная задержка между запросами
                time.sleep(random.uniform(8, 15))
            
            # Парсинг Wildberries
            if pd.notna(row['Ссылка.1']):
                wb_data = self.parse_wb_page(row['Ссылка.1'])
                company_data.update({f'WB_{k}': v for k, v in wb_data.items()})
                time.sleep(random.uniform(5, 10))
            
            results.append(company_data)
            logging.info(f"Обработана компания: {company_data['Юр. лицо']}")
            
            # Дополнительная задержка между компаниями
            time.sleep(random.uniform(10, 20))
        
        return pd.DataFrame(results)

def main():
    """Основная функция для запуска парсера"""
    try:
        # Создаем парсер
        parser = CompanyDataParser()
        
        # Обрабатываем данные из Excel
        df = parser.process_excel_data('input.xlsx')
        
        # Парсим данные для каждой строки
        results = []
        for _, row in df.iterrows():
            try:
                if row['platform'] == 'Ozon':
                    data = parser.parse_ozon_page(row['url'])
                elif row['platform'] == 'Wildberries':
                    data = parser.parse_wb_page(row['url'])
                else:
                    logging.warning(f"Неподдерживаемая платформа: {row['platform']}")
                    continue
                
                results.append(data)
            except Exception as e:
                logging.error(f"Ошибка при обработке URL {row['url']}: {str(e)}")
                continue
        
        # Сохраняем результаты в Excel
        if results:
            df_results = pd.DataFrame(results)
            df_results.to_excel('output.xlsx', index=False)
            logging.info("Результаты сохранены в output.xlsx")
        else:
            logging.warning("Нет результатов для сохранения")
            
    except Exception as e:
        logging.error(f"Ошибка при выполнении программы: {str(e)}")
        raise
    finally:
        if parser:
            parser._close_driver()

if __name__ == "__main__":
    main() 