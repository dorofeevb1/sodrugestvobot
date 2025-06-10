from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

def get_main_keyboard() -> ReplyKeyboardMarkup:
    """Создает основную клавиатуру"""
    keyboard = [
        [KeyboardButton(text="➕ Добавить товар")],
        [KeyboardButton(text="📊 Мои товары")],
        [KeyboardButton(text="📥 Скачать анализ")]
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

def get_platform_keyboard() -> InlineKeyboardMarkup:
    """Создает клавиатуру выбора платформы"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Wildberries", callback_data="wildberries"),
                InlineKeyboardButton(text="Ozon", callback_data="ozon")
            ],
            [
                InlineKeyboardButton(text="Яндекс.Маркет", callback_data="market"),
                InlineKeyboardButton(text="Отмена", callback_data="cancel")
            ]
        ]
    )
    return keyboard

def get_confirm_keyboard() -> InlineKeyboardMarkup:
    """Создает клавиатуру подтверждения"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Подтвердить", callback_data="confirm"),
                InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")
            ]
        ]
    )
    return keyboard

def get_product_keyboard(product_id: int) -> InlineKeyboardMarkup:
    """Создает клавиатуру для управления товаром"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔄 Обновить цену",
                    callback_data=f"update_price_{product_id}"
                ),
                InlineKeyboardButton(
                    text="❌ Удалить",
                    callback_data=f"delete_product_{product_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📈 История цен",
                    callback_data=f"price_history_{product_id}"
                )
            ]
        ]
    )
    return keyboard 