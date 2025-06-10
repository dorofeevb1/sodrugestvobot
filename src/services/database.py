from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager
from src.config.config import DATABASE_URL
from src.models.models import Base, User, Product, PriceHistory
from datetime import datetime
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

# Создаем движок
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

@contextmanager
def get_db():
    """Контекстный менеджер для работы с базой данных"""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception as e:
        logger.error(f"Ошибка при работе с базой данных: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()

class DatabaseService:
    @staticmethod
    def get_user(telegram_id: int):
        """Получение пользователя по telegram_id"""
        with get_db() as db:
            result = db.execute(
                select(User).where(User.telegram_id == telegram_id)
            )
            return result.scalar_one_or_none()

    @staticmethod
    def create_user(telegram_id: int, username: str = None):
        """Создание нового пользователя"""
        with get_db() as db:
            user = User(telegram_id=telegram_id, username=username)
            db.add(user)
            db.commit()
            db.refresh(user)
            return user

    @staticmethod
    def update_user_activity(telegram_id: int):
        """Обновление времени последней активности пользователя"""
        with get_db() as db:
            user = db.execute(
                select(User).where(User.telegram_id == telegram_id)
            ).scalar_one_or_none()
            
            if user:
                user.last_active = datetime.utcnow()
                db.commit()
                db.refresh(user)
            return user

    @staticmethod
    def get_user_products(telegram_id: int):
        """Получение списка товаров пользователя"""
        with get_db() as db:
            # Получаем пользователя по telegram_id
            user = db.execute(
                select(User).where(User.telegram_id == telegram_id)
            ).scalar_one_or_none()
            
            if not user:
                return []
            
            # Получаем товары пользователя
            products = db.execute(
                select(Product)
                .where(Product.user_id == user.id)
            ).scalars().all()
            
            # Преобразуем объекты в словари
            return [{
                'id': p.id,
                'name': p.name,
                'current_price': p.current_price,
                'original_price': p.original_price,
                'platform': p.platform,
                'url': p.url
            } for p in products]

    @staticmethod
    def get_product_price_history(product_id: int) -> List[Dict]:
        """Получение истории цен товара"""
        with get_db() as db:
            history = db.execute(
                select(PriceHistory)
                .where(PriceHistory.product_id == product_id)
                .order_by(PriceHistory.timestamp.desc())  # Сортировка по убыванию даты
            ).scalars().all()
            
            return [
                {
                    'id': record.id,
                    'product_id': record.product_id,
                    'price': record.price,
                    'timestamp': record.timestamp.strftime('%Y-%m-%d %H:%M:%S') if record.timestamp else None
                }
                for record in history
            ]

    @staticmethod
    def add_product(telegram_id: int, url: str, platform: str, name: str, 
                   current_price: float, original_price: float) -> Dict:
        """Добавление нового товара"""
        with get_db() as db:
            # Получаем пользователя по telegram_id
            user = db.execute(
                select(User).where(User.telegram_id == telegram_id)
            ).scalar_one_or_none()
            
            if not user:
                raise ValueError(f"Пользователь с telegram_id {telegram_id} не найден")
            
            # Проверяем, не существует ли уже такой товар
            existing_product = db.execute(
                select(Product).where(Product.url == url)
            ).scalar_one_or_none()
            
            if existing_product:
                raise ValueError(f"Товар с URL {url} уже существует")
            
            # Создаем товар
            product = Product(
                user_id=user.id,
                url=url,
                platform=platform,
                name=name,
                current_price=current_price,
                original_price=original_price
            )
            db.add(product)
            db.flush()  # Получаем ID товара без коммита
            
            # Добавляем запись в историю цен
            price_history = PriceHistory(
                product_id=product.id,
                price=current_price
            )
            db.add(price_history)
            
            # Коммитим все изменения
            db.commit()
            
            # Возвращаем копию объекта с нужными данными
            return {
                'id': product.id,
                'name': product.name,
                'current_price': product.current_price,
                'original_price': product.original_price
            }

    @staticmethod
    def update_product_price(product_id: int, new_price: float):
        """Обновление цены товара"""
        with get_db() as db:
            product = db.execute(
                select(Product).where(Product.id == product_id)
            ).scalar_one_or_none()
            
            if not product:
                raise ValueError(f"Товар с ID {product_id} не найден")
            
            product.current_price = new_price
            product.last_updated = datetime.utcnow()
            
            # Добавляем запись в историю цен
            price_history = PriceHistory(
                product_id=product_id,
                price=new_price
            )
            db.add(price_history)
            db.commit()

    @staticmethod
    def delete_product(product_id: int, telegram_id: int):
        """Удаление товара"""
        with get_db() as db:
            # Получаем пользователя
            user = db.execute(
                select(User).where(User.telegram_id == telegram_id)
            ).scalar_one_or_none()
            
            if not user:
                raise ValueError(f"Пользователь с telegram_id {telegram_id} не найден")
            
            # Получаем товар
            product = db.execute(
                select(Product)
                .where(Product.id == product_id)
                .where(Product.user_id == user.id)
            ).scalar_one_or_none()
            
            if not product:
                raise ValueError(f"Товар с ID {product_id} не найден или не принадлежит пользователю")
            
            # Удаляем товар (каскадное удаление через relationship)
            db.delete(product)
            db.commit() 