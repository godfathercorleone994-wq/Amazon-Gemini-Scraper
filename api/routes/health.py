"""
Endpoints de verificação de saúde e monitoramento de status
"""

from fastapi import APIRouter, HTTPException, Depends, status
from typing import Dict, Any, Optional
from datetime import datetime, timedelta, timezone
from enum import Enum
import psutil
import platform
import traceback

from storage.mongodb_client import get_mongodb, mongodb_client
from storage.redis_cache import redis_cache
from config.settings import settings
from utils.logger import logger

# ==================== Enumerações ====================

class HealthStatus(str, Enum):
    """Status de saúde da aplicação"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class DependencyStatus(str, Enum):
    """Status das dependências"""
    READY = "ready"
    CONNECTING = "connecting"
    UNAVAILABLE = "unavailable"
    ERROR = "error"


# ==================== Router ====================

router = APIRouter(prefix="/api/v1/health", tags=["health"])


# ==================== Endpoint: Saúde Básica ====================

@router.get("/")
async def health_check() -> Dict[str, Any]:
    """
    Verificação básica de saúde da API
    Responde rápido, sem verificar dependências
    """
    try:
        return {
            "status": HealthStatus.HEALTHY.value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "service": settings.app_name,
            "version": settings.app_version,
            "environment": settings.environment
        }
    except Exception as e:
        logger.error(f"Erro na verificação de saúde: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Falha na verificação de saúde"
        )


# ==================== Endpoint: Vivacidade (Kubernetes) ====================

@router.get("/live")
async def liveness_probe() -> Dict[str, str]:
    """
    Probe de vivacidade para Kubernetes
    Verifica se o serviço está rodando
    Resposta deve ser muito rápida
    """
    return {"status": "alive"}


# ==================== Endpoint: Prontidão (Kubernetes) ====================

@router.get("/ready")
async def readiness_probe() -> Dict[str, Any]:
    """
    Probe de prontidão para Kubernetes
    Verifica se as dependências estão prontas
    Se falhar, retorna 503
    """
    try:
        ready = True
        checks = {}
        
        # Verifica MongoDB
        mongodb_status = await _check_mongodb()
        checks["mongodb"] = mongodb_status["status"]
        
        if mongodb_status["status"] not in [
            DependencyStatus.READY.value,
            DependencyStatus.CONNECTING.value
        ]:
            ready = False
        
        # Verifica Redis
        redis_status = await _check_redis()
        checks["redis"] = redis_status["status"]
        
        if redis_status["status"] == DependencyStatus.ERROR.value:
            logger.warning("Redis indisponível, usando cache em memória")
        
        # Se não está pronto, retorna erro 503
        if not ready:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=checks
            )
        
        return {
            "status": "ready",
            "checks": checks
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro na verificação de prontidão: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": str(e)}
        )


# ==================== Endpoint: Saúde Detalhada ====================

@router.get("/detailed")
async def detailed_health() -> Dict[str, Any]:
    """
    Verificação detalhada com todas as informações
    Inclui: sistema, processo, bancos de dados, cache
    Pode levar 1-2 segundos
    """
    try:
        # Coleta métricas do sistema
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage("/")
        except Exception as e:
            logger.error(f"Erro ao coletar métricas do sistema: {str(e)}")
            cpu_percent = memory = disk = None
        
        # Coleta informações do processo
        try:
            process = psutil.Process()
            process_memory = process.memory_info()
            process_uptime = (
                datetime.now(timezone.utc) - 
                datetime.fromtimestamp(process.create_time(), tz=timezone.utc)
            ).total_seconds()
        except Exception as e:
            logger.error(f"Erro ao coletar métricas do processo: {str(e)}")
            process_memory = None
            process_uptime = 0
        
        # Verifica bancos de dados
        db_status = await _get_mongodb_status()
        cache_status = await _get_redis_status()
        
        # Verifica provedores de IA
        ai_status = {
            "gemini": "configured" if settings.gemini_api_key else "not_configured",
            "openai": "configured" if settings.openai_api_key else "not_configured",
            "huggingface": "configured" if settings.huggingface_api_key else "not_configured"
        }
        
        # Monta resposta
        response = {
            "status": HealthStatus.HEALTHY.value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "service": {
                "name": settings.app_name,
                "version": settings.app_version,
                "environment": settings.environment,
                "debug": settings.debug,
                "uptime_seconds": process_uptime
            },
            "system": _format_system_metrics(cpu_percent, memory, disk),
            "process": {
                "pid": process.pid if process else None,
                "memory": {
                    "rss": process_memory.rss if process_memory else 0,
                    "vms": process_memory.vms if process_memory else 0
                } if process_memory else {},
                "threads": process.num_threads() if process else 0,
                "connections": len(process.connections()) if process else 0
            },
            "databases": db_status,
            "cache": cache_status,
            "ai_providers": ai_status,
            "features": {
                "ml_enabled": settings.enable_ml_features,
                "notifications_enabled": settings.enable_notifications,
                "dashboard_enabled": settings.enable_dashboard,
                "webhooks_enabled": settings.enable_webhooks
            }
        }
        
        return response
        
    except Exception as e:
        logger.error(f"Erro na verificação detalhada: {str(e)}")
        return {
            "status": HealthStatus.UNHEALTHY.value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "error": str(e)
        }


# ==================== Endpoint: Métricas ====================

@router.get("/metrics")
async def get_metrics(mongodb = Depends(get_mongodb)) -> Dict[str, Any]:
    """
    Retorna métricas de desempenho da aplicação
    Inclui: cache, scraping, banco de dados
    Pode levar 1-3 segundos
    """
    try:
        # Inicializa métricas
        metrics = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "requests": {},
            "scraping": {},
            "database": {},
            "cache": {}
        }
        
        # Coleta métricas de cache
        if redis_cache._initialized:
            try:
                metrics["cache"] = await _get_cache_metrics()
            except Exception as e:
                logger.warning(f"Erro ao coletar métricas de cache: {str(e)}")
                metrics["cache"]["error"] = str(e)
        
        # Coleta métricas de scraping e banco
        try:
            metrics["scraping"] = await _get_scraping_metrics(mongodb)
            metrics["database"] = await _get_database_metrics(mongodb)
        except Exception as e:
            logger.warning(f"Erro ao coletar métricas do banco: {str(e)}")
            metrics["scraping"]["error"] = str(e)
        
        return metrics
        
    except Exception as e:
        logger.error(f"Erro ao obter métricas: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Falha ao obter métricas"
        )


# ==================== Funções Auxiliares ====================

async def _check_mongodb() -> Dict[str, str]:
    """
    Verifica conexão com MongoDB
    Retorna status: READY, CONNECTING ou ERROR
    """
    try:
        if not mongodb_client._initialized:
            return {"status": DependencyStatus.CONNECTING.value}
        
        # Tenta fazer ping no banco
        await mongodb_client.db.command("ping")
        return {"status": DependencyStatus.READY.value}
        
    except Exception as e:
        logger.warning(f"Erro ao verificar MongoDB: {str(e)}")
        return {
            "status": DependencyStatus.ERROR.value,
            "error": str(e)
        }


async def _check_redis() -> Dict[str, str]:
    """
    Verifica conexão com Redis
    Retorna status: READY, CONNECTING ou ERROR
    """
    try:
        if not redis_cache._initialized:
            return {"status": DependencyStatus.CONNECTING.value}
        
        # Tenta fazer ping no Redis
        await redis_cache.redis.ping()
        return {"status": DependencyStatus.READY.value}
        
    except Exception as e:
        logger.warning(f"Erro ao verificar Redis: {str(e)}")
        return {
            "status": DependencyStatus.ERROR.value,
            "error": str(e)
        }


async def _get_mongodb_status() -> Dict[str, Any]:
    """
    Obtém status detalhado do MongoDB
    Retorna: versão, uptime, conexões, contagem de documentos
    """
    db_status = {}
    
    try:
        # Verifica se está inicializado
        if not mongodb_client._initialized:
            db_status["mongodb"] = {"status": "not_initialized"}
            return db_status
        
        # Faz ping
        await mongodb_client.db.command("ping")
        
        # Obtém informações do servidor
        stats = await mongodb_client.db.command("serverStatus")
        
        db_status["mongodb"] = {
            "status": "ready",
            "version": stats.get("version", "unknown"),
            "uptime_seconds": stats.get("uptime", 0),
            "connections": {
                "current": stats.get("connections", {}).get("current", 0),
                "available": stats.get("connections", {}).get("available", 0)
            }
        }
        
        # Conta documentos por coleção
        collections = [
            "products",
            "extraction_results",
            "price_history",
            "reviews",
            "notifications"
        ]
        
        for collection_name in collections:
            try:
                count = await mongodb_client.db[collection_name].count_documents({})
                db_status["mongodb"][f"{collection_name}_count"] = count
            except Exception as e:
                logger.debug(f"Erro ao contar {collection_name}: {str(e)}")
        
        # Obtém estatísticas do banco
        try:
            db_stats = await mongodb_client.db.command("dbStats")
            db_status["mongodb"]["size_bytes"] = db_stats.get("dataSize", 0)
            db_status["mongodb"]["collections"] = db_stats.get("collections", 0)
            db_status["mongodb"]["indexes"] = db_stats.get("indexes", 0)
        except Exception as e:
            logger.debug(f"Erro ao obter dbStats: {str(e)}")
        
    except Exception as e:
        logger.warning(f"Erro ao verificar MongoDB: {str(e)}")
        db_status["mongodb"] = {
            "status": "error",
            "error": str(e)
        }
    
    return db_status


async def _get_redis_status() -> Dict[str, Any]:
    """
    Obtém status detalhado do Redis
    Retorna: memória usada, clientes conectados, uptime
    """
    cache_status = {}
    
    try:
        # Verifica se está inicializado
        if not redis_cache._initialized:
            cache_status["redis"] = {"status": "not_initialized"}
            return cache_status
        
        # Faz ping
        await redis_cache.redis.ping()
        
        # Obtém informações
        info = await redis_cache.redis.info()
        
        cache_status["redis"] = {
            "status": "ready",
            "memory": {
                "used_mb": info.get("used_memory_human", "unknown"),
                "max_memory_mb": info.get("maxmemory_human", "unlimited")
            },
            "connected_clients": info.get("connected_clients", 0),
            "uptime_seconds": info.get("uptime_in_seconds", 0)
        }
        
    except Exception as e:
        logger.warning(f"Erro ao verificar Redis: {str(e)}")
        cache_status["redis"] = {
            "status": "error",
            "error": str(e)
        }
    
    return cache_status


async def _get_cache_metrics() -> Dict[str, Any]:
    """
    Obtém métricas de cache
    Conta: produtos, buscas, extrações, rate limits em cache
    """
    metrics = {}
    
    try:
        # Conta chaves em cache por tipo
        product_keys = await redis_cache.redis.keys("product:*")
        search_keys = await redis_cache.redis.keys("search:*")
        extraction_keys = await redis_cache.redis.keys("extraction:*")
        rate_limit_keys = await redis_cache.redis.keys("ratelimit:*")
        
        metrics["cached_products"] = len(product_keys)
        metrics["cached_searches"] = len(search_keys)
        metrics["cached_extractions"] = len(extraction_keys)
        metrics["active_rate_limits"] = len(rate_limit_keys)
        
    except Exception as e:
        logger.warning(f"Erro ao coletar métricas de cache: {str(e)}")
        metrics["error"] = str(e)
    
    return metrics


async def _get_scraping_metrics(mongodb) -> Dict[str, Any]:
    """
    Obtém métricas de scraping
    Retorna: tarefas últimas 1h, últimas 24h, taxa de sucesso
    """
    metrics = {}
    
    try:
        # Define períodos de tempo
        now = datetime.now(timezone.utc)
        last_hour = now - timedelta(hours=1)
        last_day = now - timedelta(days=1)
        
        # Conta extrações
        recent_extractions_hour = await mongodb.db.extraction_results.count_documents({
            "started_at": {"$gte": last_hour}
        })
        
        recent_extractions_day = await mongodb.db.extraction_results.count_documents({
            "started_at": {"$gte": last_day}
        })
        
        successful_extractions_day = await mongodb.db.extraction_results.count_documents({
            "started_at": {"$gte": last_day},
            "status": "success"
        })
        
        # Calcula taxa de sucesso
        success_rate = (
            (successful_extractions_day / recent_extractions_day * 100) 
            if recent_extractions_day > 0 
            else 100
        )
        
        # Monta resultado
        metrics["last_hour"] = recent_extractions_hour
        metrics["last_day"] = recent_extractions_day
        metrics["success_rate_day"] = round(success_rate, 2)
        
    except Exception as e:
        logger.warning(f"Erro ao coletar métricas de scraping: {str(e)}")
        metrics["error"] = str(e)
    
    return metrics


async def _get_database_metrics(mongodb) -> Dict[str, Any]:
    """
    Obtém métricas do banco de dados
    Retorna: tamanho total, número de coleções, número de índices
    """
    metrics = {}
    
    try:
        # Obtém estatísticas do banco
        db_stats = await mongodb.db.command("dbStats")
        
        metrics["size_bytes"] = db_stats.get("dataSize", 0)
        metrics["collections"] = db_stats.get("collections", 0)
        metrics["indexes"] = db_stats.get("indexes", 0)
        
    except Exception as e:
        logger.warning(f"Erro ao coletar métricas do banco: {str(e)}")
        metrics["error"] = str(e)
    
    return metrics


def _format_system_metrics(
    cpu_percent: Optional[float],
    memory: Optional[psutil._pslinux.svmem],
    disk: Optional[psutil._common.sdiskusage]
) -> Dict[str, Any]:
    """
    Formata métricas do sistema em dicionário legível
    """
    try:
        return {
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "cpu": {
                "count": psutil.cpu_count(),
                "percent": round(cpu_percent, 1) if cpu_percent else 0
            },
            "memory": {
                "total": memory.total if memory else 0,
                "available": memory.available if memory else 0,
                "percent": round(memory.percent, 1) if memory else 0,
                "used": memory.used if memory else 0
            } if memory else {},
            "disk": {
                "total": disk.total if disk else 0,
                "used": disk.used if disk else 0,
                "free": disk.free if disk else 0,
                "percent": round(disk.percent, 1) if disk else 0
            } if disk else {}
        }
    except Exception as e:
        logger.error(f"Erro ao formatar métricas: {str(e)}")
        return {"error": str(e)}
