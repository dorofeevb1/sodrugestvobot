from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, create_engine, Index, text, func
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime
from src.config.config import DATABASE_URL
import logging
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import Boolean
from sqlalchemy import inspect

logger = logging.getLogger(__name__)
Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(Integer, unique=True, index=True)
    username = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_active = Column(DateTime, default=func.now())
    is_active = Column(Boolean, default=True)
    
    products = relationship("Product", back_populates="user")

    def __repr__(self):
        return f"<User(telegram_id={self.telegram_id}, username={self.username})>"

class Product(Base):
    __tablename__ = 'products'
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    url = Column(String)
    platform = Column(String)
    name = Column(String)
    current_price = Column(Float)
    discount = Column(Float, nullable=True)
    original_price = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_updated = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    user = relationship("User", back_populates="products")
    price_history = relationship("PriceHistory", back_populates="product")

    __table_args__ = (
        Index('idx_user_platform', 'user_id', 'platform'),
        Index('idx_url', 'url'),
    )

    def __repr__(self):
        return f"<Product(name={self.name}, platform={self.platform}, current_price={self.current_price})>"

class PriceHistory(Base):
    __tablename__ = 'price_history'
    
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey('products.id'))
    price = Column(Float)
    timestamp = Column(DateTime, default=func.now())
    
    product = relationship("Product", back_populates="price_history")

    __table_args__ = (
        Index('idx_product_timestamp', 'product_id', 'timestamp'),
    )

    def __repr__(self):
        return f"<PriceHistory(product_id={self.product_id}, price={self.price}, timestamp={self.timestamp})>"

def init_db(database_url: str) -> None:
    """Инициализация базы данных"""
    try:
        # Создаем движок базы данных
        engine = create_engine(database_url)
        
        # Проверяем существование таблиц
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()
        required_tables = ['users', 'products', 'price_history']
        
        # Если какие-то таблицы отсутствуют, создаем их
        if not all(table in existing_tables for table in required_tables):
            Base.metadata.create_all(engine)
            logger.info("Созданы отсутствующие таблицы")
        
        # Создаем фабрику сессий
        Session = sessionmaker(bind=engine)
        
        logger.info("База данных успешно инициализирована")
        return Session
    except Exception as e:
        logger.error(f"Ошибка при инициализации базы данных: {str(e)}")
        raise

# Создаем движок
engine = create_engine(DATABASE_URL) 