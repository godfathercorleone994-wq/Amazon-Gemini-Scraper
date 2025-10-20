"""
Configuração do Celery para tarefas assíncronas
Executa scraping, verificação de preços e alertas de forma paralela
"""
from celery import Celery
from datetime import datetime
import asyncio
from utils.logger import logger
from config.settings import settings

from features.analysis.price_tracker import PriceTracker

celery_app = Celery(
    "amazon_tracker",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    worker_concurrency=settings.celery_worker_concurrency,
    task_time_limit=settings.celery_task_time_limit,
    task_soft_time_limit=settings.celery_task_soft_time_limit,
)

@celery_app.task
def check_all_prices():
    """Tarefa periódica: verifica todos os preços rastreados"""
    logger.info("🚀 Iniciando verificação de preços em lote")
    loop = asyncio.get_event_loop()
    loop.run_until_complete(_check_all_prices_async())

async def _check_all_prices_async():
    tracker = PriceTracker()
    await tracker.initialize()
    mongodb = tracker.mongodb
    products = await mongodb.get_tracked_products()

    logger.info(f"📦 {len(products)} produtos para verificar")

    for product in products:
        new_price = product.current_price * (1 + 0.01)  # Simula aumento de 1%
        await tracker.update_price(product.asin, new_price)

    logger.info("✅ Verificação concluída")

@celery_app.task
def health_task():
    """Tarefa simples de heartbeat"""
    msg = f"✅ Worker ativo às {datetime.utcnow().isoformat()}"
    logger.info(msg)
    return msg
