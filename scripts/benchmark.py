"""
Teste de desempenho básico dos componentes
"""
import asyncio
from time import perf_counter
from storage.redis_cache import get_redis
from storage.mongodb_client import get_mongodb
from utils.logger import logger

async def run_benchmark():
    start = perf_counter()
    mongodb = await get_mongodb()
    redis = await get_redis()
    logger.info("Conexões estabelecidas")

    await redis.set("benchmark:test", {"msg": "Olá!"})
    msg = await redis.get("benchmark:test")
    logger.info(f"Redis respondendo: {msg}")

    total_products = await mongodb.products.count_documents({})
    logger.info(f"{total_products} produtos no banco")

    duration = perf_counter() - start
    logger.info(f"Benchmark concluído em {duration:.2f} segundos")

if __name__ == "__main__":
    asyncio.run(run_benchmark())
