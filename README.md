# Бот для отслеживания цен на товары

Telegram-бот для отслеживания цен на товары в различных маркетплейсах (Wildberries, Ozon, Яндекс.Маркет).

## Возможности

- Отслеживание цен на товары
- Уведомления об изменении цен
- Поддержка нескольких маркетплейсов
- История цен
- Экспорт данных

## Установка

1. Клонируйте репозиторий:
```bash
git clone https://github.com/yourusername/price-tracker-bot.git
cd price-tracker-bot
```

2. Создайте виртуальное окружение и активируйте его:
```bash
python -m venv venv
source venv/bin/activate  # для Linux/Mac
venv\Scripts\activate  # для Windows
```

3. Установите зависимости:
```bash
pip install -r requirements.txt
```

4. Создайте файл `.env` в корневой директории проекта:
```env
BOT_TOKEN=your_bot_token
DATABASE_URL=sqlite:///products.db
PARSING_TIMEOUT=30
MAX_RETRIES=3
RETRY_DELAY=5
LOG_LEVEL=INFO
```

## Запуск

```bash
python src/main.py
```

## Использование

1. Запустите бота в Telegram
2. Отправьте команду `/start`
3. Используйте команды:
   - `/add` - добавить товар для отслеживания
   - `/list` - показать список отслеживаемых товаров
   - `/delete` - удалить товар из отслеживания
   - `/help` - показать справку

## Поддерживаемые платформы

- Wildberries
- Ozon
- Яндекс.Маркет

## Требования

- Python 3.8+
- Chrome/Chromium
- Доступ к интернету

## Лицензия

MIT 