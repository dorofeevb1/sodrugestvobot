import pandas as pd
from datetime import datetime
import os
from src.services.database import DatabaseService
import logging

logger = logging.getLogger(__name__)

class AnalysisService:
    """Сервис для генерации анализа данных"""
    
    @staticmethod
    def generate_analysis(telegram_id: int) -> str:
        """
        Генерация анализа данных пользователя
        
        Args:
            telegram_id (int): ID пользователя в Telegram
            
        Returns:
            str: Путь к сгенерированному файлу
        """
        try:
            # Получаем данные пользователя
            user = DatabaseService.get_user(telegram_id)
            if not user:
                raise ValueError(f"Пользователь с telegram_id {telegram_id} не найден")
            
            # Получаем товары пользователя
            products = DatabaseService.get_user_products(telegram_id)
            
            # Создаем DataFrame с товарами
            products_df = pd.DataFrame(products)
            
            # Создаем директорию для отчетов, если её нет
            reports_dir = os.path.join(os.getcwd(), 'reports')
            os.makedirs(reports_dir, exist_ok=True)
            
            # Генерируем имя файла
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'analysis_{telegram_id}_{timestamp}.xlsx'
            filepath = os.path.join(reports_dir, filename)
            
            # Создаем Excel writer
            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                # Лист с товарами
                products_df.to_excel(writer, sheet_name='Товары', index=False)
                
                # Лист со статистикой
                stats_data = {
                    'Метрика': [
                        'Всего товаров',
                        'Средняя цена',
                        'Максимальная цена',
                        'Минимальная цена'
                    ],
                    'Значение': [
                        len(products),
                        products_df['current_price'].mean() if not products_df.empty else 0,
                        products_df['current_price'].max() if not products_df.empty else 0,
                        products_df['current_price'].min() if not products_df.empty else 0
                    ]
                }
                
                # Добавляем статистику по скидкам, если есть поле discount
                if 'discount' in products_df.columns:
                    stats_data['Метрика'].extend(['Средняя скидка', 'Максимальная скидка'])
                    stats_data['Значение'].extend([
                        products_df['discount'].mean() if not products_df.empty else 0,
                        products_df['discount'].max() if not products_df.empty else 0
                    ])
                
                pd.DataFrame(stats_data).to_excel(writer, sheet_name='Статистика', index=False)
                
                # Лист с историей цен
                if not products_df.empty:
                    history_data = []
                    for product in products:
                        history = DatabaseService.get_product_price_history(product['id'])
                        for record in history:
                            history_data.append({
                                'Товар': product['name'],
                                'Цена': record['price'],
                                'Дата': record['timestamp'] or datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                            })
                    if history_data:
                        history_df = pd.DataFrame(history_data)
                        history_df['Дата'] = pd.to_datetime(history_df['Дата'])
                        history_df = history_df.sort_values('Дата', ascending=False)
                        history_df.to_excel(writer, sheet_name='История цен', index=False)
            
            logger.info(f"Сгенерирован анализ для пользователя {telegram_id}")
            return filepath
            
        except Exception as e:
            logger.error(f"Ошибка при генерации анализа: {str(e)}")
            raise 