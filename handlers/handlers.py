from aiogram import types
from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton
from telethon import TelegramClient
import json
import logging
from datetime import datetime
from config import BOT_TOKEN, API_ID, API_HASH, SESSIONS_DIR, DATA_DIR
from parsers.marketplace_parser import parse_product
import os
from typing import Dict, Optional, Union
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError

from .keyboards import (
    get_main_keyboard,
    get_consent_keyboard,
    get_share_phone_keyboard,
    get_chats_keyboard
)

# Создаем директории, если их нет
os.makedirs(SESSIONS_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

# Инициализация Telethon клиента
telethon_client = None

async def init_telethon_client(phone: str) -> Optional[TelegramClient]:
    """Инициализация Telethon клиента"""
    try:
        session_file = os.path.join(SESSIONS_DIR, f"{phone}.session")
        client = TelegramClient(session_file, API_ID, API_HASH)
        await client.connect()
        
        if not await client.is_user_authorized():
            logging.info(f"Требуется авторизация для {phone}")
            return None
            
        return client
    except Exception as e:
        logging.error(f"Ошибка при инициализации клиента: {str(e)}")
        return None

async def cmd_start(message: types.Message):
    """Обработка команды /start"""
    welcome_text = (
        "🌟 *Добро пожаловать в Telegram User Activity Bot!*\n\n"
        "🤖 Я помогу вам отслеживать активность в ваших чатах и каналах.\n\n"
        "📋 *Что я умею:*\n"
        "• 📊 Собирать статистику активности\n"
        "• 👥 Анализировать участников чатов\n"
        "• 📈 Отслеживать изменения в группах\n"
        "• 🔔 Уведомлять о важных событиях\n\n"
        "📝 *Перед началом работы, пожалуйста, ознакомьтесь с условиями:*\n\n"
        "1️⃣ *Собираемые данные:*\n"
        "   • 👤 Ваши личные данные (имя, username)\n"
        "   • 💬 Информация о группах\n"
        "   • 📊 История взаимодействий\n\n"
        "2️⃣ *Использование данных:*\n"
        "   • 🔧 Улучшение работы бота\n"
        "   • 📈 Анализ использования\n"
        "   • 🛠 Техническая поддержка\n\n"
        "3️⃣ *Ваши права:*\n"
        "   • 🔄 Отзыв согласия в любой момент\n"
        "   • 🗑 Запрос на удаление данных\n"
        "   • 👀 Просмотр собранных данных\n\n"
        "❓ *Вы согласны с условиями сбора и обработки данных?*"
    )
    
    await message.answer(welcome_text, reply_markup=get_consent_keyboard(), parse_mode="Markdown")

async def process_consent(callback_query: types.CallbackQuery):
    """Обработка согласия пользователя"""
    user_id = callback_query.from_user.id
    
    if callback_query.data == "consent_yes":
        # Сохраняем информацию о пользователе
        save_user_info(user_id, callback_query.from_user)
        
        success_text = (
            "✅ *Спасибо за согласие!*\n\n"
            "🎉 Теперь вы можете использовать все функции бота.\n\n"
            "📱 *Доступные команды:*\n"
            "• 👤 Мои данные - просмотр информации\n"
            "• 📱 Получить список чатов - доступные чаты\n"
            "• ❌ Отозвать согласие - удаление данных\n\n"
            "🔍 *Выберите действие в меню ниже:*"
        )
        
        await callback_query.message.edit_text(success_text, reply_markup=None, parse_mode="Markdown")
        await callback_query.message.answer("👇", reply_markup=get_main_keyboard())
        
    else:
        decline_text = (
            "❌ *Вы отказались от сбора данных*\n\n"
            "😔 К сожалению, без согласия мы не можем предоставить полный функционал бота.\n\n"
            "ℹ️ Если передумаете, просто нажмите /start и дайте согласие."
        )
        
        await callback_query.message.edit_text(decline_text, reply_markup=None, parse_mode="Markdown")

async def show_user_data(message: types.Message):
    """Показать собранные данные пользователя"""
    user_id = message.from_user.id
    user_data = load_user_data(user_id)
    
    if not user_data:
        no_data_text = (
            "📭 *У вас пока нет сохраненных данных*\n\n"
            "ℹ️ Данные начнут собираться после вашего согласия и активного использования бота."
        )
        await message.answer(no_data_text, parse_mode="Markdown")
        return
    
    data_text = "📊 *Ваши данные:*\n\n"
    
    # Информация о пользователе
    user_info = user_data.get('user_info', {})
    data_text += "👤 *Личная информация:*\n"
    data_text += f"• 🆔 ID: `{user_id}`\n"
    data_text += f"• 👤 Имя: {user_info.get('first_name', 'Нет')}\n"
    data_text += f"• 👥 Фамилия: {user_info.get('last_name', 'Нет')}\n"
    data_text += f"• 📱 Username: @{user_info.get('username', 'Нет')}\n"
    data_text += f"• 📞 Телефон: `{user_info.get('phone_number', 'Нет')}`\n\n"
    
    # Добавляем информацию о чатах
    chats = user_data.get('chats', [])
    if chats:
        data_text += "💬 *Ваши чаты:*\n"
        for chat in chats:
            data_text += f"• {chat.get('title', 'Без названия')}\n"
            if chat.get('members_count'):
                data_text += f"  👥 Участников: {chat['members_count']}\n"
        data_text += "\n"
    
    # Добавляем статистику
    stats = user_data.get('stats', {})
    if stats:
        data_text += "📈 *Статистика:*\n"
        data_text += f"• 📅 Первый запуск: {stats.get('first_seen', 'Нет')}\n"
        data_text += f"• 🔄 Последний запуск: {stats.get('last_seen', 'Нет')}\n"
        data_text += f"• 📊 Всего действий: {stats.get('total_actions', 0)}\n\n"
    
    try:
        await message.answer(data_text, reply_markup=get_chats_keyboard(), parse_mode="Markdown")
    except Exception as e:
        # Если возникла ошибка с форматированием, отправляем без него
        await message.answer(
            "📊 Ваши данные:\n\n" + data_text.replace("*", "").replace("_", ""),
            reply_markup=get_chats_keyboard()
        )

async def process_get_chats(callback: types.CallbackQuery):
    """Обработка получения списка чатов"""
    try:
        if not telethon_client:
            await callback.answer(
                "❌ Клиент не инициализирован.\nПожалуйста, попробуйте позже.",
                show_alert=True
            )
            return

        # Получаем список диалогов
        dialogs = await telethon_client.get_dialogs()
        
        if not dialogs:
            await callback.answer(
                "📭 У вас нет доступных чатов",
                show_alert=True
            )
            return

        # Формируем список чатов
        chats_list = "📱 *Ваши чаты:*\n\n"
        for dialog in dialogs[:10]:  # Ограничиваем до 10 чатов
            if dialog.name:
                chats_list += f"• {dialog.name}\n"
        
        if len(dialogs) > 10:
            chats_list += f"\n...и еще {len(dialogs) - 10} чатов"

        await callback.message.edit_text(
            chats_list,
            reply_markup=get_chats_keyboard(),
            parse_mode="Markdown"
        )
        await callback.answer("✅ Список чатов обновлен")
        
    except Exception as e:
        logging.error(f"Ошибка при получении чатов: {str(e)}")
        await callback.answer(
            "❌ Произошла ошибка при получении чатов",
            show_alert=True
        )

async def process_phone(message: types.Message, state: FSMContext):
    """Обработка номера телефона"""
    try:
        if not message.contact or not message.contact.phone_number:
            await message.answer(
                "❌ Не удалось получить номер телефона.\nПожалуйста, попробуйте еще раз.",
                reply_markup=get_share_phone_keyboard()
            )
            return

        phone = message.contact.phone_number
        if not phone.startswith('+'):
            phone = '+' + phone

        # Создаем клиент
        session_file = os.path.join(SESSIONS_DIR, f"{phone}.session")
        client = TelegramClient(session_file, API_ID, API_HASH)
        await client.connect()

        if not await client.is_user_authorized():
            # Запрашиваем код подтверждения
            await message.answer(
                "📱 *Введите код подтверждения*\n\n"
                "Код был отправлен в Telegram",
                parse_mode="Markdown"
            )
            await state.set_state("waiting_for_code")
            await state.update_data(phone=phone, client=client)
            return

        # Если авторизация успешна
        global telethon_client
        telethon_client = client

        # Сохраняем данные пользователя
        user_data = {
            'phone': phone,
            'first_name': message.contact.first_name,
            'last_name': message.contact.last_name,
            'user_id': message.contact.user_id,
            'consent_given': True,
            'consent_date': datetime.now().isoformat()
        }
        
        # Сохраняем в JSON
        user_file = os.path.join(DATA_DIR, f"user_{message.from_user.id}.json")
        with open(user_file, 'w', encoding='utf-8') as f:
            json.dump(user_data, f, ensure_ascii=False, indent=2)

        await message.answer(
            "✅ *Авторизация успешна!*\n\n"
            "Теперь вы можете:\n"
            "• Просматривать свои данные\n"
            "• Получать список чатов\n"
            "• Добавлять товары для отслеживания\n"
            "• Скачивать анализ данных",
            reply_markup=get_main_keyboard(),
            parse_mode="Markdown"
        )
        await state.clear()
        
    except Exception as e:
        logging.error(f"Ошибка при обработке номера телефона: {str(e)}")
        await message.answer(
            "❌ Произошла ошибка при авторизации.\nПожалуйста, попробуйте позже.",
            reply_markup=get_main_keyboard()
        )
        await state.clear()

async def process_code(message: types.Message, state: FSMContext):
    """Обработка кода подтверждения"""
    try:
        # Получаем сохраненные данные
        data = await state.get_data()
        phone = data.get('phone')
        client = data.get('client')
        
        if not phone or not client:
            await message.answer(
                "❌ Ошибка авторизации.\nПожалуйста, начните сначала.",
                reply_markup=get_main_keyboard()
            )
            await state.clear()
            return

        try:
            # Пытаемся войти с кодом
            await client.sign_in(phone, message.text)
            
            # Если успешно
            global telethon_client
            telethon_client = client

            await message.answer(
                "✅ *Авторизация успешна!*\n\n"
                "Теперь вы можете:\n"
                "• Просматривать свои данные\n"
                "• Получать список чатов\n"
                "• Добавлять товары для отслеживания\n"
                "• Скачивать анализ данных",
                reply_markup=get_main_keyboard(),
                parse_mode="Markdown"
            )
            
        except PhoneCodeInvalidError:
            await message.answer(
                "❌ Неверный код.\nПожалуйста, попробуйте еще раз.",
                parse_mode="Markdown"
            )
            return
            
        except SessionPasswordNeededError:
            await message.answer(
                "🔐 *Требуется пароль двухфакторной аутентификации*\n\n"
                "Пожалуйста, введите пароль:",
                parse_mode="Markdown"
            )
            await state.set_state("waiting_for_password")
            return
            
        except Exception as e:
            logging.error(f"Ошибка при вводе кода: {str(e)}")
            await message.answer(
                "❌ Произошла ошибка при авторизации.\nПожалуйста, попробуйте позже.",
                reply_markup=get_main_keyboard()
            )
            await state.clear()
            return

    except Exception as e:
        logging.error(f"Ошибка при обработке кода: {str(e)}")
        await message.answer(
            "❌ Произошла ошибка.\nПожалуйста, попробуйте позже.",
            reply_markup=get_main_keyboard()
        )
        await state.clear()

async def process_password(message: types.Message, state: FSMContext):
    """Обработка пароля двухфакторной аутентификации"""
    try:
        # Получаем сохраненные данные
        data = await state.get_data()
        client = data.get('client')
        
        if not client:
            await message.answer(
                "❌ Ошибка авторизации.\nПожалуйста, начните сначала.",
                reply_markup=get_main_keyboard()
            )
            await state.clear()
            return

        try:
            # Пытаемся войти с паролем
            await client.sign_in(password=message.text)
            
            # Если успешно
            global telethon_client
            telethon_client = client

            await message.answer(
                "✅ *Авторизация успешна!*\n\n"
                "Теперь вы можете:\n"
                "• Просматривать свои данные\n"
                "• Получать список чатов\n"
                "• Добавлять товары для отслеживания\n"
                "• Скачивать анализ данных",
                reply_markup=get_main_keyboard(),
                parse_mode="Markdown"
            )
            
        except Exception as e:
            logging.error(f"Ошибка при вводе пароля: {str(e)}")
            await message.answer(
                "❌ Неверный пароль.\nПожалуйста, попробуйте еще раз.",
                parse_mode="Markdown"
            )
            return

    except Exception as e:
        logging.error(f"Ошибка при обработке пароля: {str(e)}")
        await message.answer(
            "❌ Произошла ошибка.\nПожалуйста, попробуйте позже.",
            reply_markup=get_main_keyboard()
        )
        await state.clear()

async def get_user_chats(message: types.Message, user_id: int):
    """Получение и отображение списка чатов пользователя"""
    try:
        if not telethon_client:
            error_text = (
                "❌ *Ошибка*\n\n"
                "⚠️ Клиент не инициализирован.\n"
                "Пожалуйста, попробуйте позже."
            )
            await message.answer(error_text, parse_mode="Markdown")
            return
            
        loading_text = (
            "🔄 *Загрузка чатов...*\n\n"
            "⏳ Пожалуйста, подождите.\n"
            "Это может занять некоторое время."
        )
        status_message = await message.answer(loading_text, parse_mode="Markdown")
        
        chats = []
        async for dialog in telethon_client.iter_dialogs():
            try:
                entity = dialog.entity
                chat_info = {
                    'id': entity.id,
                    'title': getattr(entity, 'title', None) or getattr(entity, 'first_name', 'Unknown'),
                    'type': 'channel' if getattr(entity, 'broadcast', False) else 'group' if getattr(entity, 'megagroup', False) else 'private',
                    'members_count': getattr(entity, 'participants_count', None),
                    'username': getattr(entity, 'username', None)
                }
                
                if chat_info['title']:
                    chats.append(chat_info)
                    
            except Exception as e:
                logging.error(f"Error processing dialog: {str(e)}")
                continue
        
        if not chats:
            no_chats_text = (
                "📭 *У вас нет доступных чатов*\n\n"
                "ℹ️ Бот может работать только с чатами, где вы являетесь участником."
            )
            await status_message.edit_text(no_chats_text, parse_mode="Markdown")
            return
            
        # Формируем сообщение
        text = "📱 *Ваши чаты:*\n\n"
        for chat in chats:
            # Определяем эмодзи в зависимости от типа чата
            chat_emoji = "📢" if chat['type'] == 'channel' else "👥" if chat['type'] == 'group' else "👤"
            
            text += f"{chat_emoji} *{chat['title']}*"
            if chat['username']:
                text += f" (@{chat['username']})"
            if chat['members_count']:
                text += f"\n   👥 Участников: {chat['members_count']}"
            text += "\n\n"
        
        await status_message.edit_text(text, parse_mode="Markdown")
        
    except Exception as e:
        error_text = (
            "❌ *Ошибка при получении списка чатов*\n\n"
            f"⚠️ Произошла ошибка:\n`{str(e)}`\n\n"
            "🔄 Пожалуйста, попробуйте позже."
        )
        await message.answer(error_text, parse_mode="Markdown")

def save_user_info(user_id: int, user: types.User, phone: str = None):
    """Сохранение информации о пользователе"""
    user_id = str(user_id)
    data_file = f'{DATA_DIR}/user_{user_id}.json'
    
    try:
        # Загружаем существующие данные
        try:
            with open(data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            data = {'user_info': {}, 'actions': []}
        
        # Обновляем информацию
        data['user_info'].update({
            'username': user.username,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'phone_number': phone,
            'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
        
        # Сохраняем данные
        with open(data_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            
    except Exception as e:
        logging.error(f"Error saving user info: {str(e)}")

def load_user_data(user_id: int) -> dict:
    """Загрузка данных пользователя"""
    user_id = str(user_id)
    data_file = f'{DATA_DIR}/user_{user_id}.json'
    
    try:
        with open(data_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_session(user_id: int, phone: str) -> bool:
    """Сохранение информации о сессии"""
    session_file = f'{SESSIONS_DIR}/session_{user_id}.json'
    
    try:
        session_info = {
            'user_id': user_id,
            'phone': phone,
            'session_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        with open(session_file, 'w') as f:
            json.dump(session_info, f)
        return True
    except Exception as e:
        logging.error(f"Error saving session: {str(e)}")
        return False

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
            data = await parse_product(link)
            
            if not data:
                await status_message.edit_text(
                    "❌ *Ошибка при парсинге товара*\n\n"
                    "⚠️ Не удалось получить данные о товаре.\n"
                    "Пожалуйста, проверьте ссылку и попробуйте снова.",
                    parse_mode="Markdown"
                )
                return
            
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

def create_product_card(data: Dict) -> str:
    """Создание карточки товара для отображения"""
    try:
        # Форматирование цены
        price = f"{data['price']:,.0f}".replace(',', ' ')
        old_price = f"{data['old_price']:,.0f}".replace(',', ' ') if data.get('old_price') else None
        
        # Форматирование скидки
        discount = data.get('discount', 0)
        discount_text = f"🎯 *Скидка:* {discount}%" if discount > 0 else ""
        
        # Форматирование рейтинга
        rating = data.get('rating', 0)
        stars = "⭐" * int(rating) + "☆" * (5 - int(rating))
        
        # Форматирование отзывов
        reviews = data.get('reviews', 0)
        reviews_text = f"📝 *Отзывы:* {reviews:,}".replace(',', ' ')
        
        # Сборка карточки
        card = (
            f"🏷️ *{data['name']}*\n\n"
            f"💰 *Цена:* {price} ₽"
        )
        
        if old_price:
            card += f"\n💸 *Старая цена:* {old_price} ₽"
        
        if discount_text:
            card += f"\n{discount_text}"
        
        if data.get('brand'):
            card += f"\n🏭 *Бренд:* {data['brand']}"
        
        if rating > 0:
            card += f"\n\n{stars}"
            card += f"\n{reviews_text}"
        
        return card
        
    except Exception as e:
        logging.error(f"Ошибка при создании карточки товара: {str(e)}")
        return "❌ Ошибка при отображении данных товара"

def add_link_to_file(link: str) -> bool:
    """Добавление ссылки в файл links.txt"""
    try:
        with open('links.txt', 'a', encoding='utf-8') as f:
            f.write(f"\n{link}")
        return True
    except Exception as e:
        logging.error(f"Ошибка при добавлении ссылки: {str(e)}")
        return False

def read_parsed_data() -> Dict:
    """Чтение данных из JSON файла"""
    try:
        with open('parsed_data.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

async def show_data(message: types.Message):
    """Показать все спарсенные данные"""
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

async def download_analysis(message: types.Message):
    """Скачать анализ данных в Excel"""
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
        import pandas as pd
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

async def add_product(message: types.Message, state: FSMContext):
    """Запрос ссылки на товар"""
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
    await state.set_state("waiting_for_link") 