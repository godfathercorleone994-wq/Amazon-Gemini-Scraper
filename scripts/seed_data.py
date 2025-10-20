"""
Popula o banco de dados com dados de demonstração
"""
import asyncio
from datetime import datetime
from storage.mongodb_client import get_mongodb
from utils.logger import logger
from models.product import Product

async def seed():
    mongodb = await get_mongodb()
    logger.info("Populando dados de exemplo...")
    sample_products = [
        Product(
            asin="B08N5WRWNW",
            url="https://amazon.com/dp/B08N5WRWNW",
            title="Echo Dot 4th Gen",
            brand="Amazon",
            current_price=49.99,
            currency="USD",
            status="in_stock",
            is_tracked=True,
            scraped_at=datetime.utcnow()
        ),
        Product(
            asin="B07XJ8C8F5",
            url="https://amazon.com/dp/B07XJ8C8F5",
            title="Fire TV Stick 4K",
            brand="Amazon",
            current_price=39.99,
            currency="USD",
            status="in_stock",
            is_tracked=True,
            scraped_at=datetime.utcnow()
        )
    ]
    for product in sample_products:
        await mongodb.save_product(product)
    logger.info("Dados de exemplo inseridos com sucesso!")

if __name__ == "__main__":
    asyncio.run(seed())
