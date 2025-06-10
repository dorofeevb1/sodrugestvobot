import asyncio
import json
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from companies_data import CompanyDataParser
import pandas as pd
from datetime import datetime
import os
from users_info import save_user_info, get_all_users
from logger import activity_logger, logger

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)

# Инициализация бота
BOT_TOKEN = '7631678487:AAEDXa77p9hNOtf7Z2NVPq-fJjB6Sl9s2ck'
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Состояния FSM
class ProductStates(StatesGroup):
    waiting_for_link = State()

def read_parsed_data():
    """Чтение данных из JSON файла"""
    try:
        with open('parsed_data.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"Ошибка при чтении данных: {str(e)}")
        return {}

def add_link_to_file(link: str):
    """Добавление ссылки в файл links.txt"""
    try:
        with open('links.txt', 'a', encoding='utf-8') as f:
            f.write(f"\n{link}")
        return True
    except Exception as e:
        logging.error(f"Ошибка при добавлении ссылки: {str(e)}")
        return False

def get_main_keyboard():
    """Создание основной клавиатуры"""
    keyboard = ReplyKeyboardMarkup(
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
    return keyboard

def create_product_card(item_data: dict) -> str:
    """Создание красивой карточки товара"""
    platform_emoji = "🛍️" if item_data.get('platform') == 'Ozon' else "🛒"
    discount = ""
    if item_data.get('price_with_discount') and item_data.get('price_without_discount'):
        try:
            price_with = float(item_data['price_with_discount'].replace('₽', '').replace(' ', '').strip())
            price_without = float(item_data['price_without_discount'].replace('₽', '').replace(' ', '').strip())
            if price_without > price_with:
                discount_percent = int((1 - price_with / price_without) * 100)
                discount = f"\n🎯 *Скидка:* {discount_percent}%"
        except:
            pass

    return (
        f"{platform_emoji} *{item_data.get('platform', 'Не указано')}*\n\n"
        f"📦 *Название:*\n{item_data.get('product_name', 'Не указано')}\n\n"
        f"💰 *Цена со скидкой:* {item_data.get('price_with_discount', 'Не указано')}\n"
        f"💵 *Цена без скидки:* {item_data.get('price_without_discount', 'Не указано')}"
        f"{discount}\n"
    )

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    """Обработка команды /start"""
    # Логируем информацию о пользователе
    activity_logger.log_user_info(
        message.from_user.id,
        message.from_user.username,
        message.from_user.first_name,
        message.from_user.last_name
    )
    
    # Логируем действие
    activity_logger.log_user_action(
        message.from_user.id,
        "start_command",
        {"chat_id": message.chat.id}
    )
    
    # Create keyboard buttons
    buttons = [
        [KeyboardButton(text="➕ Добавить товар"), KeyboardButton(text="📊 Показать данные")],
        [KeyboardButton(text="📈 Скачать анализ"), KeyboardButton(text="ℹ️ Помощь")]
    ]
    
    # Create keyboard markup
    markup = ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True
    )
    
    await message.answer(
        f"👋 Привет, {message.from_user.first_name}!\n\n"
        "Я бот для анализа цен на товары в разных маркетплейсах.\n\n"
        "Что я умею:\n"
        "• Добавлять товары для отслеживания\n"
        "• Анализировать цены на разных площадках\n"
        "• Парсить актуальные цены\n"
        "• Показывать статистику и скидки\n\n"
        "Выберите действие в меню ниже 👇",
        reply_markup=markup
    )

@dp.message(Command("stats"))
async def show_stats(message: types.Message):
    """Show detailed statistics about bot users"""
    # Логируем действие
    activity_logger.log_user_action(
        message.from_user.id,
        "stats_command",
        {"chat_id": message.chat.id}
    )
    
    stats = activity_logger.get_all_stats()
    if not stats:
        await message.answer("📊 Статистика пока пуста")
        return
    
    stats_text = "📊 *Подробная статистика пользователей:*\n\n"
    for user_id, data in stats.items():
        user_info = data.get('user_info', {})
        stats_text += f"*ID:* {user_id}\n"
        stats_text += f"*Имя:* {user_info.get('first_name', 'Нет')}\n"
        stats_text += f"*Фамилия:* {user_info.get('last_name', 'Нет')}\n"
        stats_text += f"*Username:* @{user_info.get('username', 'Нет')}\n"
        stats_text += f"*Первый запуск:* {data.get('first_seen', 'Нет')}\n"
        stats_text += f"*Последний запуск:* {data.get('last_seen', 'Нет')}\n"
        
        # Добавляем статистику действий
        actions = data.get('actions', [])
        stats_text += f"*Всего действий:* {len(actions)}\n"
        if actions:
            stats_text += "*Последние действия:*\n"
            for action in actions[-3:]:  # Показываем последние 3 действия
                stats_text += f"• {action['action']} ({action['timestamp']})\n"
        
        stats_text += "-------------------\n"
    
    await message.answer(stats_text, parse_mode="Markdown")

@dp.message(lambda message: message.text == "ℹ️ Помощь")
async def show_help(message: types.Message):
    """Обработка показа помощи"""
    activity_logger.log_user_action(
        message.from_user.id,
        "help_button",
        {"chat_id": message.chat.id}
    )
    await message.answer(
        "📚 *Справка по использованию бота*\n\n"
        "1️⃣ *Показать данные*\n"
        "Показывает список всех отслеживаемых товаров с текущими ценами\n\n"
        "2️⃣ *Добавить товар*\n"
        "Добавляет новый товар для отслеживания\n"
        "Поддерживаемые магазины:\n"
        "• Ozon\n"
        "• Wildberries\n\n"
        "3️⃣ *Скачать анализ*\n"
        "Создает Excel-файл с полной информацией о товарах\n\n"
        "❓ *Как добавить товар:*\n"
        "1. Нажмите '➕ Добавить товар'\n"
        "2. Отправьте ссылку на товар\n"
        "3. Дождитесь результата парсинга\n\n"
        "⚠️ *Важно:*\n"
        "• Используйте только ссылки с Ozon или Wildberries\n"
        "• Парсинг может занять 30-60 секунд\n"
        "• При ошибке попробуйте позже",
        parse_mode="Markdown"
    )

@dp.message(lambda message: message.text == "📊 Показать данные")
async def show_data(message: types.Message):
    """Обработка показа данных"""
    activity_logger.log_user_action(
        message.from_user.id,
        "show_data_button",
        {"chat_id": message.chat.id}
    )
    data = read_parsed_data()
    if not data:
        await message.answer(
            "📭 *Нет данных для отображения*\n\n"
            "Добавьте товары для отслеживания, нажав кнопку '➕ Добавить товар'",
            parse_mode="Markdown"
        )
        return
    
    await message.answer(
        "🔄 *Загружаю данные...*\n\n"
        f"📦 Всего товаров: {len(data)}",
        parse_mode="Markdown"
    )
    
    for url, item_data in data.items():
        text = create_product_card(item_data)
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🔗 Открыть товар", url=url)]
            ]
        )
        await message.answer(text, reply_markup=keyboard, parse_mode="Markdown")

@dp.message(lambda message: message.text == "📈 Скачать анализ")
async def download_analysis(message: types.Message):
    """Обработка скачивания анализа"""
    activity_logger.log_user_action(
        message.from_user.id,
        "download_analysis_button",
        {"chat_id": message.chat.id}
    )
    try:
        data = read_parsed_data()
        if not data:
            await message.answer(
                "📭 *Нет данных для анализа*\n\n"
                "Добавьте товары для отслеживания, нажав кнопку '➕ Добавить товар'",
                parse_mode="Markdown"
            )
            return
        
        await message.answer("⏳ *Подготовка файла анализа...*", parse_mode="Markdown")
        
        # Создаем DataFrame
        df = pd.DataFrame.from_dict(data, orient='index')
        
        # Добавляем дату анализа
        df['date_analyzed'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Сохраняем в Excel
        filename = f'analysis_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        
        try:
            df.to_excel(filename, index=True, engine='openpyxl')
            
            # Отправляем файл
            from aiogram.types import FSInputFile
            file = FSInputFile(filename)
            await message.answer_document(
                document=file,
                caption="📊 *Анализ данных по товарам*\n\n"
                       "📋 Файл содержит:\n"
                       "• Названия товаров\n"
                       "• Текущие цены\n"
                       "• Скидки\n"
                       "• Дату анализа",
                parse_mode="Markdown"
            )
            
            # Удаляем временный файл
            os.remove(filename)
            
        except Exception as e:
            logging.error(f"Ошибка при создании Excel файла: {str(e)}")
            await message.answer(
                f"❌ *Ошибка при создании файла анализа:*\n{str(e)}",
                parse_mode="Markdown"
            )
            
    except Exception as e:
        logging.error(f"Ошибка при подготовке анализа: {str(e)}")
        await message.answer(
            f"❌ *Произошла ошибка при подготовке анализа:*\n{str(e)}",
            parse_mode="Markdown"
        )

@dp.message(lambda message: message.text == "➕ Добавить товар")
async def add_product(message: types.Message, state: FSMContext):
    """Запрос ссылки на товар"""
    activity_logger.log_user_action(
        message.from_user.id,
        "add_product_button",
        {"chat_id": message.chat.id}
    )
    await message.answer(
        "🔗 *Отправьте ссылку на товар*\n\n"
        "📌 *Поддерживаемые магазины:*\n"
        "• 🛍️ Ozon\n"
        "• 🛒 Wildberries\n\n"
        "⚠️ *Важно:*\n"
        "• Используйте только ссылки с этих магазинов\n"
        "• Парсинг может занять 30-60 секунд",
        parse_mode="Markdown"
    )
    await state.set_state(ProductStates.waiting_for_link)

@dp.message(ProductStates.waiting_for_link)
async def process_link(message: types.Message, state: FSMContext):
    """Обработка полученной ссылки"""
    link = message.text.strip()
    
    # Проверка валидности ссылки
    if not (link.startswith('https://www.ozon.ru/') or link.startswith('https://www.wildberries.ru/')):
        await message.answer(
            "❌ *Неверная ссылка!*\n\n"
            "📌 *Поддерживаемые магазины:*\n"
            "• 🛍️ Ozon\n"
            "• 🛒 Wildberries\n\n"
            "⚠️ Пожалуйста, отправьте ссылку с одного из этих магазинов",
            parse_mode="Markdown"
        )
        return
    
    # Добавление ссылки в файл
    if add_link_to_file(link):
        status_message = await message.answer(
            "⏳ *Начинаю парсинг товара...*\n\n"
            "🔄 Это может занять некоторое время\n"
            "⏱️ Обычно процесс занимает 30-60 секунд",
            parse_mode="Markdown"
        )
        
        # Парсинг товара
        parser = CompanyDataParser()
        try:
            # Определяем платформу
            platform = "Wildberries" if "wildberries" in link else "Ozon"
            platform_emoji = "🛒" if platform == "Wildberries" else "🛍️"
            
            await status_message.edit_text(
                f"⏳ *Парсинг товара с {platform_emoji} {platform}...*\n\n"
                "🔄 Загрузка страницы и извлечение данных\n"
                "⏱️ Пожалуйста, подождите",
                parse_mode="Markdown"
            )
            
            # Парсим данные
            data = parser.parse_wb_page(link) if 'wildberries' in link else parser.parse_ozon_page(link)
            
            # Сохраняем данные
            current_data = read_parsed_data()
            current_data[link] = data
            with open('parsed_data.json', 'w', encoding='utf-8') as f:
                json.dump(current_data, f, ensure_ascii=False, indent=2)
            
            # Показываем результат
            text = create_product_card(data)
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="🔗 Открыть товар", url=link)]
                ]
            )
            
            await status_message.edit_text(
                "✅ *Товар успешно добавлен и спарсен!*\n\n" + text,
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
            
        except Exception as e:
            logging.error(f"Ошибка при парсинге товара: {str(e)}")
            await status_message.edit_text(
                f"❌ *Ошибка при парсинге товара:*\n{str(e)}",
                parse_mode="Markdown"
            )
    else:
        await message.answer(
            "❌ *Произошла ошибка при добавлении ссылки.*",
            parse_mode="Markdown"
        )
    
    await state.clear()

async def main():
    """Запуск бота"""
    try:
        logging.info("Бот запущен")
        await dp.start_polling(bot)
    except Exception as e:
        logging.error(f"Ошибка при работе бота: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main()) 