import logging
import time
from companies_data import CompanyDataParser
from typing import List, Dict
import json

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('parser.log'),
        logging.StreamHandler()
    ]
)

def read_links_from_file(filename: str) -> List[str]:
    """Чтение ссылок из файла"""
    try:
        with open(filename, 'r') as f:
            return [line.strip() for line in f if line.strip()]
    except Exception as e:
        logging.error(f"Ошибка при чтении файла {filename}: {str(e)}")
        return []

def main():
    # Инициализация парсера
    parser = CompanyDataParser()
    
    # Чтение ссылок из файла
    links = read_links_from_file('links.txt')
    if not links:
        logging.error("Не удалось прочитать ссылки из файла")
        return
    
    # Словарь для хранения результатов
    results = {}
    
    # Обработка каждой ссылки
    for url in links:
        try:
            logging.info(f"Обработка ссылки: {url}")
        
            # Определяем маркетплейс по URL
            if 'ozon.ru' in url:
                data = parser.parse_ozon_page(url)
            elif 'wildberries.ru' in url:
                data = parser.parse_wb_page(url)
        else:
                logging.warning(f"Неизвестный маркетплейс для URL: {url}")
                continue
            
            if data:
                results[url] = data
                logging.info(f"Успешно получены данные для {url}")
        else:
                logging.warning(f"Не удалось получить данные для {url}")
        
            # Пауза между запросами
            time.sleep(5)
            
        except Exception as e:
            logging.error(f"Ошибка при обработке {url}: {str(e)}")
            continue
    
    # Сохранение результатов в JSON
    try:
        with open('parsed_data.json', 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=4)
        logging.info("Результаты сохранены в parsed_data.json")
    except Exception as e:
        logging.error(f"Ошибка при сохранении результатов: {str(e)}")

if __name__ == "__main__":
    main() 