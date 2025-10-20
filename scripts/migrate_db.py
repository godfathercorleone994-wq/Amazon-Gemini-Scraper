"""
Script de migração de banco de dados MongoDB
Cria índices e estruturas iniciais
"""
import asyncio
from storage.mongodb_client import get_mongodb
from utils.logger import logger

async def migrate():
    logger.info("Iniciando migração...")
    mongodb = await get_mongodb()
    await mongodb._create_indexes()
    logger.info("Migração concluída.")

if __name__ == "__main__":
    asyncio.run(migrate())
