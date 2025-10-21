"""
Gerenciador de Webhooks para integração com sistemas externos
Permite que aplicações recebam notificações em tempo real via HTTP
"""
import httpx
import asyncio
import hashlib
import hmac
import json
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from urllib.parse import urlparse
import uuid

from config.settings import settings
from utils.logger import logger
from storage.mongodb_client import get_mongodb
from storage.redis_cache import get_redis

class WebhookManager:
    """
    Gerenciador de webhooks para notificações HTTP
    
    Funcionalidades:
    - Registro e validação de webhooks
    - Envio assíncrono com retry
    - Assinatura HMAC para segurança
    - Rate limiting por endpoint
    - Histórico de entregas
    - Suporte a diferentes formatos (JSON, form-data)
    """
    
    def __init__(self):
        """
        Inicializa o gerenciador de webhooks
        
        Configura cliente HTTP com timeouts e retry policy
        """
        # Cliente HTTP com configurações otimizadas
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0),  # 30 segundos de timeout
            limits=httpx.Limits(
                max_keepalive_connections=20,
                max_connections=100
            ),
            headers={
                "User-Agent": f"{settings.app_name}/{settings.app_version}"
            }
        )
        
        # Configurações de retry
        self.max_retries = 3
        self.retry_delay = 5  # segundos
        self.backoff_factor = 2  # Multiplicador para backoff exponencial
        
        # Rate limiting
        self.rate_limits = {}  # Armazena limites por domínio
        
    async def __aenter__(self):
        """Suporte para context manager async"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Fecha cliente HTTP ao sair do context"""
        await self.client.aclose()
    
    async def register_webhook(
        self,
        url: str,
        events: List[str],
        secret: Optional[str] = None,
        description: Optional[str] = None,
        user_id: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        active: bool = True
    ) -> Dict[str, Any]:
        """
        Registra um novo webhook no sistema
        
        Args:
            url: URL do endpoint que receberá as notificações
            events: Lista de eventos para receber (price_drop, back_in_stock, etc)
            secret: Segredo para assinatura HMAC (gerado automaticamente se não fornecido)
            description: Descrição do webhook
            user_id: ID do usuário proprietário
            headers: Headers customizados para enviar
            active: Se o webhook está ativo
            
        Returns:
            Dict com dados do webhook registrado
            
        Raises:
            ValueError: Se a URL for inválida
            
        Example:
            >>> manager = WebhookManager()
            >>> webhook = await manager.register_webhook(
            ...     url="https://myapp.com/webhook",
            ...     events=["price_drop", "back_in_stock"],
            ...     description="Meu webhook de produção"
            ... )
        """
        # Valida URL
        if not await self.validate_webhook(url):
            raise ValueError(f"URL inválida ou inacessível: {url}")
        
        # Gera secret se não fornecido
        if not secret:
            secret = self._generate_secret()
        
        # Extrai domínio para rate limiting
        parsed_url = urlparse(url)
        domain = parsed_url.netloc
        
        # Cria registro do webhook
        webhook_data = {
            "webhook_id": str(uuid.uuid4()),
            "url": url,
            "domain": domain,
            "events": events,
            "secret": secret,
            "description": description,
            "user_id": user_id,
            "custom_headers": headers or {},
            "active": active,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "last_triggered": None,
            "total_calls": 0,
            "successful_calls": 0,
            "failed_calls": 0,
            "last_error": None,
            "metadata": {
                "ip_address": None,  # Será preenchido na primeira chamada
                "response_time_avg": 0,
                "last_status_code": None
            }
        }
        
        # Salva no MongoDB
        try:
            mongodb = await get_mongodb()
            await mongodb.db.webhooks.insert_one(webhook_data)
            
            logger.info(
                f"Webhook registrado: {webhook_data['webhook_id']}",
                url=url,
                events=events
            )
            
            # Envia notificação de teste
            await self._send_test_notification(webhook_data)
            
            return webhook_data
            
        except Exception as e:
            logger.error(f"Erro ao registrar webhook: {str(e)}")
            raise
    
    async def validate_webhook(self, url: str, timeout: int = 10) -> bool:
        """
        Valida se a URL do webhook é acessível
        
        Args:
            url: URL para validar
            timeout: Timeout em segundos
            
        Returns:
            bool: True se a URL é válida e acessível
            
        Note:
            Faz uma requisição HEAD para verificar disponibilidade
            Aceita códigos 200-299 e 405 (método não permitido para HEAD)
        """
        try:
            # Valida formato da URL
            parsed = urlparse(url)
            if not parsed.scheme in ['http', 'https']:
                logger.warning(f"Esquema inválido na URL: {parsed.scheme}")
                return False
            
            if not parsed.netloc:
                logger.warning(f"Domínio inválido na URL: {url}")
                return False
            
            # Testa conectividade
            response = await self.client.head(
                url,
                timeout=timeout,
                follow_redirects=True
            )
            
            # Aceita 200-299 ou 405 (método HEAD não permitido, mas endpoint existe)
            if response.status_code < 300 or response.status_code == 405:
                logger.info(f"Webhook validado com sucesso: {url}")
                return True
            
            logger.warning(f"Webhook retornou status {response.status_code}: {url}")
            return False
            
        except httpx.TimeoutException:
            logger.warning(f"Timeout ao validar webhook: {url}")
            return False
        except Exception as e:
            logger.error(f"Erro ao validar webhook: {str(e)}")
            return False
    
    async def send_webhook(
        self,
        url: str,
        data: Dict[str, Any],
        event_type: str = "notification",
        secret: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        retry: bool = True
    ) -> Dict[str, Any]:
        """
        Envia notificação para webhook
        
        Args:
            url: URL do webhook
            data: Dados para enviar (serão convertidos para JSON)
            event_type: Tipo do evento
            secret: Segredo para assinatura HMAC
            headers: Headers customizados
            retry: Se deve tentar novamente em caso de falha
            
        Returns:
            Dict com resultado do envio
            
        Example:
            >>> manager = WebhookManager()
            >>> result = await manager.send_webhook(
            ...     url="https://myapp.com/webhook",
            ...     data={"product": "B08N5WRWNW", "price": 29.99},
            ...     event_type="price_drop"
            ... )
        """
        # Prepara payload
        payload = {
            "event": event_type,
            "timestamp": datetime.utcnow().isoformat(),
            "data": data,
            "metadata": {
                "source": settings.app_name,
                "version": settings.app_version
            }
        }
        
        # Serializa para JSON
        json_payload = json.dumps(payload, default=str)
        
        # Prepara headers
        request_headers = {
            "Content-Type": "application/json",
            "X-Webhook-Event": event_type,
            "X-Webhook-Timestamp": str(int(datetime.utcnow().timestamp())),
            "X-Webhook-ID": str(uuid.uuid4())
        }
        
        # Adiciona assinatura HMAC se secret fornecido
        if secret:
            signature = self._generate_signature(json_payload, secret)
            request_headers["X-Webhook-Signature"] = signature
        
        # Merge com headers customizados
        if headers:
            request_headers.update(headers)
        
        # Tenta enviar com retry
        attempt = 0
        last_error = None
        
        while attempt <= (self.max_retries if retry else 0):
            try:
                # Verifica rate limiting
                if not await self._check_rate_limit(url):
                    await asyncio.sleep(60)  # Aguarda 1 minuto
                    continue
                
                # Registra tentativa
                attempt += 1
                logger.info(f"Enviando webhook para {url} (tentativa {attempt})")
                
                # Envia requisição
                start_time = datetime.utcnow()
                response = await self.client.post(
                    url,
                    content=json_payload,
                    headers=request_headers,
                    timeout=30.0
                )
                end_time = datetime.utcnow()
                
                # Calcula tempo de resposta
                response_time = (end_time - start_time).total_seconds()
                
                # Verifica sucesso
                if response.status_code < 300:
                    logger.info(
                        f"Webhook enviado com sucesso: {url}",
                        status_code=response.status_code,
                        response_time=response_time
                    )
                    
                    # Atualiza estatísticas
                    await self._update_webhook_stats(
                        url,
                        success=True,
                        response_time=response_time,
                        status_code=response.status_code
                    )
                    
                    return {
                        "success": True,
                        "status_code": response.status_code,
                        "response_time": response_time,
                        "attempts": attempt,
                        "response_body": response.text[:500]  # Primeiros 500 chars
                    }
                
                # Status de erro
                logger.warning(
                    f"Webhook retornou erro: {url}",
                    status_code=response.status_code,
                    response=response.text[:200]
                )
                
                last_error = f"HTTP {response.status_code}: {response.text[:200]}"
                
                # Se for erro 4xx (cliente), não tenta novamente
                if 400 <= response.status_code < 500:
                    break
                
            except httpx.TimeoutException as e:
                last_error = f"Timeout: {str(e)}"
                logger.warning(f"Timeout no webhook {url}: {str(e)}")
                
            except Exception as e:
                last_error = str(e)
                logger.error(f"Erro ao enviar webhook {url}: {str(e)}")
            
            # Aguarda antes do retry (backoff exponencial)
            if attempt <= self.max_retries and retry:
                delay = self.retry_delay * (self.backoff_factor ** (attempt - 1))
                logger.info(f"Aguardando {delay}s antes do retry...")
                await asyncio.sleep(delay)
        
        # Falhou após todas tentativas
        logger.error(
            f"Webhook falhou após {attempt} tentativas: {url}",
            last_error=last_error
        )
        
        # Atualiza estatísticas de falha
        await self._update_webhook_stats(
            url,
            success=False,
            last_error=last_error
        )
        
        return {
            "success": False,
            "attempts": attempt,
            "error": last_error
        }
    
    async def send_batch(
        self,
        webhooks: List[Dict[str, Any]],
        data: Dict[str, Any],
        event_type: str = "notification"
    ) -> Dict[str, Dict[str, Any]]:
        """
        Envia notificação para múltiplos webhooks em paralelo
        
        Args:
            webhooks: Lista de webhooks [{url, secret, headers}, ...]
            data: Dados para enviar
            event_type: Tipo do evento
            
        Returns:
            Dict com resultado para cada webhook
            
        Note:
            Usa asyncio.gather para envio paralelo
            Limita concorrência para evitar sobrecarga
        """
        results = {}
        
        # Limita concorrência
        MAX_CONCURRENT = 10
        semaphore = asyncio.Semaphore(MAX_CONCURRENT)
        
        async def send_with_limit(webhook: Dict[str, Any]):
            """Envia webhook respeitando limite de concorrência"""
            async with semaphore:
                return await self.send_webhook(
                    url=webhook['url'],
                    data=data,
                    event_type=event_type,
                    secret=webhook.get('secret'),
                    headers=webhook.get('headers')
                )
        
        # Envia todos em paralelo
        tasks = []
        for webhook in webhooks:
            task = send_with_limit(webhook)
            tasks.append(task)
        
        # Aguarda conclusão
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Mapeia resultados
        for webhook, response in zip(webhooks, responses):
            if isinstance(response, Exception):
                results[webhook['url']] = {
                    "success": False,
                    "error": str(response)
                }
            else:
                results[webhook['url']] = response
        
        # Log resumo
        successful = sum(1 for r in results.values() if r.get('success'))
        logger.info(
            f"Batch webhook enviado: {successful}/{len(webhooks)} sucesso",
            event_type=event_type
        )
        
        return results
    
    async def trigger_event(
        self,
        event_type: str,
        data: Dict[str, Any],
        user_id: Optional[str] = None
    ):
        """
        Dispara evento para todos webhooks inscritos
        
        Args:
            event_type: Tipo do evento (price_drop, back_in_stock, etc)
            data: Dados do evento
            user_id: ID do usuário (opcional, para filtrar webhooks)
            
        Example:
            >>> await manager.trigger_event(
            ...     event_type="price_drop",
            ...     data={
            ...         "asin": "B08N5WRWNW",
            ...         "old_price": 49.99,
            ...         "new_price": 29.99
            ...     }
            ... )
        """
        try:
            mongodb = await get_mongodb()
            
            # Busca webhooks ativos para este evento
            query = {
                "active": True,
                "events": event_type
            }
            
            if user_id:
                query["user_id"] = user_id
            
            webhooks = await mongodb.db.webhooks.find(query).to_list(100)
            
            if not webhooks:
                logger.info(f"Nenhum webhook encontrado para evento {event_type}")
                return
            
            logger.info(
                f"Disparando evento {event_type} para {len(webhooks)} webhooks"
            )
            
            # Envia para todos webhooks
            results = await self.send_batch(
                webhooks=[
                    {
                        "url": w["url"],
                        "secret": w.get("secret"),
                        "headers": w.get("custom_headers")
                    }
                    for w in webhooks
                ],
                data=data,
                event_type=event_type
            )
            
            # Atualiza último disparo
            for webhook in webhooks:
                await mongodb.db.webhooks.update_one(
                    {"webhook_id": webhook["webhook_id"]},
                    {
                        "$set": {"last_triggered": datetime.utcnow()},
                        "$inc": {"total_calls": 1}
                    }
                )
            
        except Exception as e:
            logger.error(f"Erro ao disparar evento {event_type}: {str(e)}")
    
    def _generate_signature(self, payload: str, secret: str) -> str:
        """
        Gera assinatura HMAC SHA256 para o payload
        
        Args:
            payload: Conteúdo para assinar
            secret: Chave secreta
            
        Returns:
            str: Assinatura hex
            
        Note:
            Usa HMAC-SHA256 para garantir integridade
            Formato: sha256=<signature>
        """
        signature = hmac.new(
            secret.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return f"sha256={signature}"
    
    def verify_signature(self, payload: str, signature: str, secret: str) -> bool:
        """
        Verifica assinatura HMAC de um webhook recebido
        
        Args:
            payload: Conteúdo recebido
            signature: Assinatura recebida (formato: sha256=...)
            secret: Chave secreta
            
        Returns:
            bool: True se assinatura é válida
            
        Example:
            >>> # No seu endpoint que recebe webhooks:
            >>> signature = request.headers.get("X-Webhook-Signature")
            >>> is_valid = manager.verify_signature(
            ...     request.body,
            ...     signature,
            ...     webhook_secret
            ... )
        """
        expected_signature = self._generate_signature(payload, secret)
        
        # Comparação segura contra timing attacks
        return hmac.compare_digest(signature, expected_signature)
    
    def _generate_secret(self) -> str:
        """
        Gera secret aleatório para webhook
        
        Returns:
            str: Secret de 32 caracteres
        """
        import secrets
        return secrets.token_urlsafe(32)
    
    async def _check_rate_limit(self, url: str) -> bool:
        """
        Verifica rate limiting para domínio
        
        Args:
            url: URL do webhook
            
        Returns:
            bool: True se pode enviar, False se limite excedido
            
        Note:
            Implementa rate limiting por domínio
            Default: 100 requisições por minuto
        """
        parsed = urlparse(url)
        domain = parsed.netloc
        
        # Configuração de rate limit (pode vir do banco)
        limit = self.rate_limits.get(domain, 100)  # 100 req/min default
        period = 60  # segundos
        
        try:
            redis = await get_redis()
            key = f"webhook_rate:{domain}"
            
            # Incrementa contador
            current = await redis.increment(key)
            
            # Define expiração na primeira requisição
            if current == 1:
                await redis.expire(key, period)
            
            # Verifica limite
            if current > limit:
                logger.warning(
                    f"Rate limit excedido para {domain}: {current}/{limit}"
                )
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Erro ao verificar rate limit: {str(e)}")
            return True  # Permite em caso de erro
    
    async def _update_webhook_stats(
        self,
        url: str,
        success: bool,
        response_time: Optional[float] = None,
        status_code: Optional[int] = None,
        last_error: Optional[str] = None
    ):
        """
        Atualiza estatísticas do webhook
        
        Args:
            url: URL do webhook
            success: Se o envio foi bem-sucedido
            response_time: Tempo de resposta em segundos
            status_code: Código HTTP retornado
            last_error: Último erro ocorrido
        """
        try:
            mongodb = await get_mongodb()
            
            # Prepara update
            update = {
                "$set": {
                    "updated_at": datetime.utcnow()
                },
                "$inc": {}
            }
            
            if success:
                update["$inc"]["successful_calls"] = 1
            else:
                update["$inc"]["failed_calls"] = 1
                if last_error:
                    update["$set"]["last_error"] = last_error
                    update["$set"]["last_error_at"] = datetime.utcnow()
            
            if response_time:
                update["$set"]["metadata.last_response_time"] = response_time
            
            if status_code:
                update["$set"]["metadata.last_status_code"] = status_code
            
            # Atualiza webhook
            await mongodb.db.webhooks.update_one(
                {"url": url},
                update
          )
        except Exception as e:
            logger.error(f"Erro ao atualizar stats do webhook: {str(e)}")
    
    async def _send_test_notification(self, webhook_data: Dict[str, Any]):
        """
        Envia notificação de teste para webhook recém-registrado
        
        Args:
            webhook_data: Dados do webhook
        """
        test_data = {
            "test": True,
            "message": "Webhook registrado com sucesso!",
            "webhook_id": webhook_data["webhook_id"],
            "events": webhook_data["events"]
        }
        
        await self.send_webhook(
            url=webhook_data["url"],
            data=test_data,
            event_type="webhook.test",
            secret=webhook_data.get("secret"),
      headers=webhook_data.get("custom_headers"),
            retry=False  # Não faz retry para teste
        )
    
    async def get_webhook_stats(self, webhook_id: str) -> Dict[str, Any]:
        """
        Obtém estatísticas detalhadas de um webhook
        
        Args:
            webhook_id: ID do webhook
            
        Returns:
            Dict com estatísticas
        """
        try:
            mongodb = await get_mongodb()
            
            webhook = await mongodb.db.webhooks.find_one(
                {"webhook_id": webhook_id}
            )
            
            if not webhook:
                return {}
              # Calcula métricas
            total = webhook.get("total_calls", 0)
            successful = webhook.get("successful_calls", 0)
            failed = webhook.get("failed_calls", 0)
            
            success_rate = (successful / total * 100) if total > 0 else 0
            
            return {
                "webhook_id": webhook_id,
                "url": webhook["url"],
                "active": webhook.get("active", False),
                "created_at": webhook.get("created_at"),
                "last_triggered": webhook.get("last_triggered"),
                "statistics": {
                    "total_calls": total,
                    "successful_calls": successful,
                    "failed_calls": failed,
                    "success_rate": round(success_rate, 2),
                    "last_error": webhook.get("last_error"),
                    "avg_response_time": webhook.get("metadata", {}).get("response_time_avg", 0)
          }
            }
            
        except Exception as e:
            logger.error(f"Erro ao obter stats do webhook: {str(e)}")
            return {}
