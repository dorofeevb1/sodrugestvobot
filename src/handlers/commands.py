import os
import csv
import tempfile
import logging
from datetime import datetime
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, FSInputFile
from src.services.database import DatabaseService
from src.services.parser import ParserService
from src.keyboards.keyboards import get_main_keyboard, get_product_keyboard, get_platform_keyboard, get_confirm_keyboard
from src.utils.user import ensure_user_exists
from src.utils.validators import validate_url
from src.services.analysis import AnalysisService
from src.services.bulk_importer import BulkImporterService

logger = logging.getLogger(__name__)
router = Router()

# Создаем экземпляр ParserService
parser_service = ParserService()

class ProductStates(StatesGroup):
    """Состояния для добавления товара"""
    waiting_for_url = State()
    waiting_for_platform = State()
    waiting_for_confirm = State()

def get_main_keyboard() -> ReplyKeyboardMarkup:
    """Создает основную клавиатуру"""
    keyboard = [
        [KeyboardButton(text="➕ Добавить товар")],
        [KeyboardButton(text="📊 Мои товары")],
        [KeyboardButton(text="📥 Скачать анализ")]
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

@router.message(Command("start"))
async def cmd_start(message: Message):
    """Обработчик команды /start"""
    try:
        # Получаем или создаем пользователя
        user = DatabaseService.get_user(message.from_user.id)
        if not user:
            user = DatabaseService.create_user(
                telegram_id=message.from_user.id,
                username=message.from_user.username
            )
            logger.info(f"Создан новый пользователь: {message.from_user.id}")
        else:
            DatabaseService.update_user_activity(message.from_user.id)
            logger.info(f"Обновлена активность пользователя: {message.from_user.id}")
        
        await message.answer(
            "👋 Привет! Я бот для отслеживания цен на товары.\n\n"
            "Я могу помочь вам следить за ценами на товары в различных магазинах.\n"
            "Просто отправьте мне ссылку на товар, и я начну отслеживать его цену.",
            reply_markup=get_main_keyboard()
        )
    except Exception as e:
        logger.error(f"Ошибка при обработке команды /start: {str(e)}")
        await message.answer(
            "😔 Произошла ошибка при запуске бота. Пожалуйста, попробуйте позже."
        )

@router.message(Command("help"))
async def cmd_help(message: Message):
    """Обработчик команды /help"""
    help_text = (
        "🤖 Я бот для отслеживания цен на товары.\n\n"
        "Доступные команды:\n"
        "/start - Начать работу с ботом\n"
        "/help - Показать это сообщение\n"
        "/add - Добавить новый товар для отслеживания\n"
        "/list - Показать список отслеживаемых товаров\n"
        "/delete - Удалить товар из отслеживания\n\n"
        "Чтобы добавить товар для отслеживания:\n"
        "1. Нажмите кнопку 'Добавить товар' или отправьте команду /add\n"
        "2. Выберите платформу\n"
        "3. Отправьте ссылку на товар\n"
        "4. Подтвердите добавление\n\n"
        "Я буду регулярно проверять цены и уведомлять вас об изменениях!"
    )
    await message.answer(help_text)

@router.message(Command("add"))
@router.message(F.text == "➕ Добавить товар")
async def cmd_add(message: Message, state: FSMContext):
    """Обработчик команды /add и кнопки добавления товара"""
    try:
        await message.answer(
            "Выберите платформу:",
            reply_markup=get_platform_keyboard()
        )
        await state.set_state(ProductStates.waiting_for_platform)
    except Exception as e:
        logger.error(f"Ошибка при обработке команды /add: {str(e)}")
        await message.answer(
            "😔 Произошла ошибка. Пожалуйста, попробуйте позже."
        )

@router.callback_query(ProductStates.waiting_for_platform)
async def process_platform_selection(callback: CallbackQuery, state: FSMContext):
    """Обработчик выбора платформы"""
    try:
        platform = callback.data
        await state.update_data(platform=platform)
        
        await callback.message.edit_text(
            f"Выбрана платформа: {platform}\n\n"
            "Теперь отправьте мне ссылку на товар."
        )
        await state.set_state(ProductStates.waiting_for_url)
    except Exception as e:
        logger.error(f"Ошибка при выборе платформы: {str(e)}")
        await callback.message.edit_text(
            "😔 Произошла ошибка. Пожалуйста, попробуйте снова."
        )

@router.message(ProductStates.waiting_for_url)
async def process_url(message: Message, state: FSMContext):
    """Обработчик ввода URL"""
    try:
        url = message.text.strip()
        
        # Валидация URL
        if not validate_url(url):
            await message.answer(
                "❌ Неверный формат URL. Пожалуйста, отправьте корректную ссылку."
            )
            return
        
        # Получаем данные о товаре
        data = await state.get_data()
        platform = data.get('platform')
        
        if not platform:
            await message.answer(
                "❌ Ошибка: платформа не выбрана. Пожалуйста, начните сначала с команды /add"
            )
            await state.clear()
            return
        
        try:
            product_data = await parser_service.get_product_data(url, platform)
        except Exception as e:
            logger.error(f"Ошибка при парсинге товара: {str(e)}")
            await message.answer(
                "❌ Не удалось получить информацию о товаре. "
                "Пожалуйста, проверьте ссылку и попробуйте снова."
            )
            return
        
        # Сохраняем данные о товаре
        await state.update_data(
            url=url,
            name=product_data['name'],
            current_price=product_data['current_price'],
            original_price=product_data['original_price']
        )
        
        # Формируем сообщение с информацией о товаре
        product_info = (
            f"📦 Товар: {product_data['name']}\n"
            f"💰 Текущая цена: {product_data['current_price']} ₽\n"
            f"💵 Обычная цена: {product_data['original_price']} ₽\n"
            f"🏷 Скидка: {product_data['discount']}%\n\n"
            "Подтвердите добавление товара:"
        )
        
        await message.answer(
            product_info,
            reply_markup=get_confirm_keyboard()
        )
        await state.set_state(ProductStates.waiting_for_confirm)
    except Exception as e:
        logger.error(f"Ошибка при обработке URL: {str(e)}")
        await message.answer(
            "😔 Произошла ошибка. Пожалуйста, попробуйте снова."
        )

@router.callback_query(ProductStates.waiting_for_confirm)
async def process_confirmation(callback: CallbackQuery, state: FSMContext):
    """Обработчик подтверждения добавления товара"""
    try:
        if callback.data == "confirm":
            # Получаем данные о товаре
            data = await state.get_data()
            
            try:
                # Добавляем товар в базу данных
                product = DatabaseService.add_product(
                    telegram_id=callback.from_user.id,
                    url=data['url'],
                    platform=data['platform'],
                    name=data['name'],
                    current_price=data['current_price'],
                    original_price=data['original_price']
                )
                
                await callback.message.edit_text(
                    f"✅ Товар успешно добавлен!\n\n"
                    f"📦 {product['name']}\n"
                    f"💰 Текущая цена: {product['current_price']} ₽\n"
                    f"💵 Обычная цена: {product['original_price']} ₽"
                )
            except ValueError as e:
                await callback.message.edit_text(
                    f"❌ {str(e)}"
                )
            except Exception as e:
                logger.error(f"Ошибка при добавлении товара: {str(e)}")
                await callback.message.edit_text(
                    "😔 Произошла ошибка при добавлении товара. "
                    "Пожалуйста, попробуйте позже."
                )
        else:
            await callback.message.edit_text(
                "❌ Добавление товара отменено."
            )
        
        # Сбрасываем состояние
        await state.clear()
    except Exception as e:
        logger.error(f"Ошибка при подтверждении добавления товара: {str(e)}")
        await callback.message.edit_text(
            "😔 Произошла ошибка. Пожалуйста, попробуйте снова."
        )

@router.message(Command("list"))
@router.message(F.text == "📋 Список товаров")
async def cmd_list(message: Message):
    """Обработчик команды /list и кнопки списка товаров"""
    try:
        # Получаем список товаров пользователя
        products = DatabaseService.get_user_products(message.from_user.id)
        
        if not products:
            await message.answer(
                "📝 У вас пока нет отслеживаемых товаров.\n"
                "Используйте команду /add чтобы добавить товар."
            )
            return
        
        # Формируем сообщение со списком товаров
        response = "📋 Ваши отслеживаемые товары:\n\n"
        for product in products:
            response += (
                f"📦 {product['name']}\n"
                f"💰 Текущая цена: {product['current_price']} ₽\n"
                f"💵 Обычная цена: {product['original_price']} ₽\n"
                f"🔗 {product['url']}\n\n"
            )
        
        await message.answer(response)
    except Exception as e:
        logger.error(f"Ошибка при получении списка товаров: {str(e)}")
        await message.answer(
            "😔 Произошла ошибка при получении списка товаров. "
            "Пожалуйста, попробуйте позже."
        )

@router.message(Command("delete"))
@router.message(F.text == "❌ Удалить товар")
async def cmd_delete(message: Message):
    """Обработчик команды /delete и кнопки удаления товара"""
    try:
        # Получаем список товаров пользователя
        products = DatabaseService.get_user_products(message.from_user.id)
        
        if not products:
            await message.answer(
                "📝 У вас пока нет отслеживаемых товаров.\n"
                "Используйте команду /add чтобы добавить товар."
            )
            return
        
        # Формируем сообщение со списком товаров для удаления
        response = "🗑 Выберите товар для удаления:\n\n"
        for i, product in enumerate(products, 1):
            response += (
                f"{i}. {product['name']}\n"
                f"   💰 {product['current_price']} ₽\n"
            )
        
        await message.answer(response)
    except Exception as e:
        logger.error(f"Ошибка при подготовке удаления товара: {str(e)}")
        await message.answer(
            "😔 Произошла ошибка. Пожалуйста, попробуйте позже."
        )

@router.message(F.text == "📊 Мои товары")
async def show_products(message: Message):
    """Обработчик кнопки 'Мои товары'"""
    try:
        # Получаем товары пользователя
        products = DatabaseService.get_user_products(message.from_user.id)
        
        if not products:
            await message.answer(
                "📝 У вас пока нет отслеживаемых товаров.\n"
                "Используйте кнопку '➕ Добавить товар' чтобы добавить товар."
            )
            return
        
        # Отправляем информацию о каждом товаре
        for product in products:
            message_text = (
                f"📦 {product['name']}\n"
                f"💰 Текущая цена: {product['current_price']} ₽\n"
                f"🏷️ Платформа: {product['platform']}\n"
                f"🔗 Ссылка: {product['url']}"
            )
            
            await message.answer(
                message_text,
                reply_markup=get_product_keyboard(product['id'])
            )
            
    except Exception as e:
        logger.error(f"Ошибка при показе товаров: {str(e)}")
        await message.answer(
            "❌ Произошла ошибка при получении списка товаров.\n"
            "Пожалуйста, попробуйте позже."
        )

@router.message(F.text == "📥 Скачать анализ")
async def download_analysis(message: Message):
    """Обработчик кнопки 'Скачать анализ'"""
    try:
        # Проверяем наличие товаров
        products = DatabaseService.get_user_products(message.from_user.id)
        if not products:
            await message.answer(
                "📝 У вас пока нет отслеживаемых товаров.\n"
                "Используйте кнопку '➕ Добавить товар' чтобы добавить товар."
            )
            return

        # Отправляем сообщение о начале генерации
        status_message = await message.answer(
            "🔄 Генерирую анализ данных...\n"
            "Это может занять некоторое время."
        )
        
        # Генерируем анализ
        filepath = AnalysisService.generate_analysis(message.from_user.id)
        
        # Отправляем файл
        await message.answer_document(
            document=FSInputFile(filepath),
            caption="📊 Ваш анализ данных готов!\n\n"
                   "В файле вы найдете:\n"
                   "• Список всех ваших товаров\n"
                   "• Статистику по ценам и скидкам\n"
                   "• Историю изменения цен"
        )
        
        # Удаляем сообщение о статусе
        await status_message.delete()
        
        # Удаляем файл после отправки
        os.remove(filepath)
        
    except Exception as e:
        logger.error(f"Ошибка при генерации анализа: {str(e)}")
        await message.answer(
            "❌ Произошла ошибка при генерации анализа.\n"
            "Пожалуйста, попробуйте позже."
        )

@router.message(F.text == "🔄 Обновить цены")
async def update_prices(message: Message):
    """Обработчик кнопки обновления цен"""
    try:
        # Проверяем существование пользователя
        if not await ensure_user_exists(message.from_user.id, message.from_user.username):
            await message.answer("Пожалуйста, начните с команды /start")
            return

        # Получаем все товары пользователя
        products = DatabaseService.get_user_products(message.from_user.id)
        if not products:
            await message.answer("У вас пока нет отслеживаемых товаров.")
            return

        # Отправляем сообщение о начале обновления
        status_message = await message.answer("Начинаю обновление цен...")

        # Обновляем цены для каждого товара
        for i, product in enumerate(products, 1):
            try:
                # Парсим данные
                product_data = await parser_service.parse_product(product['url'])
                if not product_data:
                    await message.answer(f"Не удалось получить данные для товара: {product['name']}")
                    continue

                # Обновляем цену
                DatabaseService.update_product_price(product['id'], product_data['current_price'])

                # Обновляем статус
                await status_message.edit_text(
                    f"Обновлено {i} из {len(products)} товаров...\n"
                    f"Последний товар: {product['name']}"
                )

            except Exception as e:
                logger.error(f"Ошибка при обновлении цены товара {product['name']}: {str(e)}")
                await message.answer(f"Ошибка при обновлении цены товара {product['name']}: {str(e)}")

        # Отправляем сообщение об успешном завершении
        await status_message.edit_text(
            f"Обновление цен завершено!\n"
            f"Обновлено {len(products)} товаров."
        )

    except Exception as e:
        logger.error(f"Ошибка при обновлении цен: {str(e)}")
        await message.answer("Произошла ошибка при обновлении цен. Пожалуйста, попробуйте позже.")

@router.message(F.text == "📋 Парсить ссылки из файла")
async def parse_links_from_file(message: Message):
    """Обработчик кнопки парсинга ссылок из файла"""
    try:
        # Проверяем существование пользователя
        if not await ensure_user_exists(message.from_user.id, message.from_user.username):
            await message.answer("Пожалуйста, начните с команды /start")
            return

        # Проверяем существование файла
        if not os.path.exists('links.txt'):
            await message.answer("Файл links.txt не найден. Пожалуйста, создайте файл с ссылками.")
            return

        # Читаем ссылки из файла
        with open('links.txt', 'r', encoding='utf-8') as file:
            links = [line.strip() for line in file if line.strip()]

        if not links:
            await message.answer("Файл links.txt пуст. Добавьте ссылки для парсинга.")
            return

        # Отправляем сообщение о начале парсинга
        status_message = await message.answer("Начинаю парсинг ссылок...")

        # Парсим каждую ссылку
        for i, link in enumerate(links, 1):
            try:
                # Парсим данные
                product_data = await parser_service.parse_product(link)
                if not product_data:
                    await message.answer(f"Не удалось получить данные для ссылки: {link}")
                    continue

                # Сохраняем товар
                DatabaseService.add_product(
                    telegram_id=message.from_user.id,
                    url=link,
                    platform=product_data['platform'],
                    name=product_data['name'],
                    current_price=product_data['current_price'],
                    original_price=product_data.get('original_price', product_data['current_price'])
                )

                # Обновляем статус
                await status_message.edit_text(
                    f"Обработано {i} из {len(links)} ссылок...\n"
                    f"Последний товар: {product_data['name']}"
                )

            except Exception as e:
                logger.error(f"Ошибка при парсинге ссылки {link}: {str(e)}")
                await message.answer(f"Ошибка при обработке ссылки {link}: {str(e)}")

        # Отправляем сообщение об успешном завершении
        await status_message.edit_text(
            f"Парсинг завершен!\n"
            f"Обработано {len(links)} ссылок."
        )

    except Exception as e:
        logger.error(f"Ошибка при парсинге ссылок: {str(e)}")
        await message.answer("Произошла ошибка при парсинге ссылок. Пожалуйста, попробуйте позже.")

@router.message(Command("import"))
async def cmd_import(message: Message):
    """Обработчик команды /import"""
    try:
        # Проверяем наличие файла
        file_path = "links.txt"
        if not os.path.exists(file_path):
            await message.answer(
                "❌ Файл links.txt не найден.\n"
                "Пожалуйста, убедитесь, что файл находится в корневой директории бота."
            )
            return
        
        # Отправляем сообщение о начале импорта
        status_message = await message.answer(
            "🔄 Начинаю импорт товаров из файла...\n"
            "Это может занять некоторое время."
        )
        
        # Импортируем товары
        importer = BulkImporterService()
        results = await importer.import_from_file(message.from_user.id, file_path)
        
        # Формируем отчет
        report = "📊 Результаты импорта:\n\n"
        
        if results['success']:
            report += f"✅ Успешно добавлены ({len(results['success'])}):\n"
            for item in results['success']:
                report += f"• {item}\n"
            report += "\n"
        
        if results['errors']:
            report += f"❌ Ошибки ({len(results['errors'])}):\n"
            for error in results['errors']:
                report += f"• {error}\n"
        
        # Отправляем отчет
        await message.answer(report)
        
        # Удаляем сообщение о статусе
        await status_message.delete()
        
    except Exception as e:
        logger.error(f"Ошибка при импорте товаров: {str(e)}")
        await message.answer(
            "❌ Произошла ошибка при импорте товаров.\n"
            "Пожалуйста, попробуйте позже."
        ) 