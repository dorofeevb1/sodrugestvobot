from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

def get_main_keyboard() -> ReplyKeyboardMarkup:
    """Создает основную клавиатуру"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="📊 Показать данные"),
                KeyboardButton(text="➕ Добавить товар")
            ],
            [
                KeyboardButton(text="📈 Скачать анализ"),
                KeyboardButton(text="ℹ️ Помощь")
            ]
        ],
        resize_keyboard=True
    )

def get_product_keyboard(url: str) -> InlineKeyboardMarkup:
    """Создает клавиатуру для товара"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔗 Открыть товар", url=url)]
        ]
    )

def get_analysis_keyboard() -> InlineKeyboardMarkup:
    """Создает клавиатуру для анализа"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📊 График цен", callback_data="price_graph"),
                InlineKeyboardButton(text="📈 Статистика", callback_data="price_stats")
            ],
            [
                InlineKeyboardButton(text="📉 Скидки", callback_data="discounts"),
                InlineKeyboardButton(text="📋 Экспорт", callback_data="export")
            ]
        ]
    ) 