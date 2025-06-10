import pytest
from src.services.parser import ParserService
from unittest.mock import Mock, patch

@pytest.fixture
async def parser():
    async with ParserService() as p:
        yield p

@pytest.mark.asyncio
async def test_parse_ozon_valid_url(parser):
    # Подготовка
    url = "https://www.ozon.ru/product/test"
    mock_html = """
    <h1>Test Product</h1>
    <span data-testid="price">1000 ₽</span>
    """
    
    with patch.object(parser, '_make_request', return_value=mock_html):
        # Действие
        result = await parser.parse_ozon(url)
        
        # Проверка
        assert result is not None
        assert result['platform'] == 'Ozon'
        assert result['name'] == 'Test Product'
        assert result['current_price'] == 1000.0

@pytest.mark.asyncio
async def test_parse_wildberries_valid_url(parser):
    # Подготовка
    url = "https://www.wildberries.ru/catalog/test"
    mock_html = """
    <h1>Test Product</h1>
    <span class="price-block__price">2000 ₽</span>
    """
    
    with patch.object(parser, '_make_request', return_value=mock_html):
        # Действие
        result = await parser.parse_wildberries(url)
        
        # Проверка
        assert result is not None
        assert result['platform'] == 'Wildberries'
        assert result['name'] == 'Test Product'
        assert result['current_price'] == 2000.0

@pytest.mark.asyncio
async def test_parse_invalid_url(parser):
    # Подготовка
    url = "https://invalid-url.com"
    
    # Действие
    result = await parser.parse_product(url)
    
    # Проверка
    assert result is None

@pytest.mark.asyncio
async def test_parse_request_failure(parser):
    # Подготовка
    url = "https://www.ozon.ru/product/test"
    
    with patch.object(parser, '_make_request', return_value=None):
        # Действие
        result = await parser.parse_ozon(url)
        
        # Проверка
        assert result is None

@pytest.mark.asyncio
async def test_parse_invalid_html(parser):
    # Подготовка
    url = "https://www.ozon.ru/product/test"
    mock_html = "<invalid>html</invalid>"
    
    with patch.object(parser, '_make_request', return_value=mock_html):
        # Действие
        result = await parser.parse_ozon(url)
        
        # Проверка
        assert result is None 