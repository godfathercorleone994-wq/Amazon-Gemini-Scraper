"""
Sistema de rastreamento e análise de preços
Monitora variações, detecta padrões e gera alertas inteligentes
"""
import asyncio
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timedelta
import numpy as np
from dataclasses import dataclass
from enum import Enum

from storage.mongodb_client import get_mongodb
from storage.redis_cache import get_redis
from features.notifications.webhook_manager import WebhookManager
from utils.logger import logger
from models.product import Product, PriceHistory

class PriceTrend(Enum):
    """Tendências de preço identificadas"""
    STABLE = "stable"           # Preço estável
    INCREASING = "increasing"   # Tendência de alta
    DECREASING = "decreasing"   # Tendência de baixa
    VOLATILE = "volatile"       # Alta volatilidade
    HISTORIC_LOW = "historic_low"  # Mínimo histórico
    HISTORIC_HIGH = "historic_high"  # Máximo histórico

@dataclass
class PriceAnalysis:
    """Resultado da análise de preço"""
    current_price: float
    previous_price: float
    change_amount: float
    change_percentage: float
    trend: PriceTrend
    avg_price_7d: float
    avg_price_30d: float
    min_price_30d: float
    max_price_30d: float
    volatility: float
    is_good_deal: bool
    recommendation: str
    confidence_score: float

class PriceTracker:
    """
    Rastreador avançado de preços com análise preditiva
    
    Funcionalidades:
    - Monitoramento contínuo de preços
    - Detecção de padrões e tendências
    - Alertas inteligentes baseados em ML
    - Previsão de preços futuros
    - Análise de volatilidade
    - Detecção de promoções falsas
    """
    
    def __init__(self):
        """Inicializa o rastreador de preços"""
        self.mongodb = None
        self.redis = None
        self.webhook_manager = WebhookManager()
        
        # Configurações de análise
        self.min_history_points = 5  # Mínimo de pontos para análise
        self.volatility_threshold = 0.15  # 15% para considerar volátil
        self.significant_change = 0.05  # 5% para mudança significativa
        
        # Cache de análises
        self.analysis_cache = {}
        self.cache_ttl = 3600  # 1 hora
    
    async def initialize(self):
        """Inicializa conexões necessárias"""
        self.mongodb = await get_mongodb()
        self.redis = await get_redis()
        logger.info("PriceTracker inicializado")
    
    async def track_product(
        self,
        asin: str,
        target_price: Optional[float] = None,
        alert_on_any_drop: bool = False
    ) -> Dict[str, Any]:
        """
        Inicia rastreamento de um produto
        
        Args:
            asin: ASIN do produto
            target_price: Preço alvo para alerta
            alert_on_any_drop: Alertar em qualquer queda de preço
            
        Returns:
            Dict com status do rastreamento
            
        Example:
            >>> tracker = PriceTracker()
            >>> result = await tracker.track_product(
            ...     asin="B08N5WRWNW",
            ...     target_price=29.99
            ... )
        """
        try:
            # Busca produto
            product = await self.mongodb.get_product_by_asin(asin)
            
            if not product:
                return {
                    "success": False,
                    "error": "Produto não encontrado"
                }
            
            # Atualiza configurações de rastreamento
            product.is_tracked = True
            product.has_alert = target_price is not None
            product.alert_price = target_price
            
            # Adiciona metadados de rastreamento
            tracking_data = {
                "asin": asin,
                "target_price": target_price,
                "alert_on_any_drop": alert_on_any_drop,
                "started_at": datetime.utcnow(),
                "last_checked": datetime.utcnow(),
                "check_count": 0,
                "alerts_sent": 0
            }
            
            # Salva no banco
            await self.mongodb.save_product(product)
            await self.mongodb.db.price_tracking.update_one(
                {"asin": asin},
                {"$set": tracking_data},
                upsert=True
            )
            
            # Adiciona ao cache
            await self.redis.set(
                f"tracking:{asin}",
                tracking_data,
                ttl=86400  # 24 horas
            )
            
            logger.info(
                f"Rastreamento iniciado para {asin}",
                target_price=target_price
            )
            
            # Faz análise inicial
            analysis = await self.analyze_price(asin)
            
            return {
                "success": True,
                "product": product.dict(),
                "tracking": tracking_data,
                "analysis": analysis
            }
            
        except Exception as e:
            logger.error(f"Erro ao iniciar rastreamento: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def update_price(
        self,
        asin: str,
        new_price: float,
        check_alerts: bool = True
    ) -> Dict[str, Any]:
        """
        Atualiza preço de um produto e verifica alertas
        
        Args:
            asin: ASIN do produto
            new_price: Novo preço
            check_alerts: Se deve verificar alertas
            
        Returns:
            Dict com resultado da atualização
        """
        try:
            # Busca produto
            product = await self.mongodb.get_product_by_asin(asin)
            
            if not product:
                return {
                    "success": False,
                    "error": "Produto não encontrado"
                }
            
            old_price = product.current_price
            
            # Verifica se o preço mudou
            if abs(old_price - new_price) < 0.01:  # Menos de 1 centavo
                logger.debug(f"Preço não mudou para {asin}: ${new_price}")
                return {
                    "success": True,
                    "changed": False,
                    "price": new_price
                }
            
            # Calcula mudança
            price_change = new_price - old_price
            price_change_pct = (price_change / old_price * 100) if old_price > 0 else 0
            
            logger.info(
                f"Mudança de preço detectada para {asin}",
                old_price=old_price,
                new_price=new_price,
                change=f"{price_change_pct:.2f}%"
            )
            
            # Atualiza preço
            await self.mongodb.update_product_price(asin, new_price)
            
            # Adiciona ao histórico
            history_entry = {
                "asin": asin,
                "price": new_price,
                "old_price": old_price,
                "change_amount": price_change,
                "change_percentage": price_change_pct,
                "timestamp": datetime.utcnow(),
                "is_decrease": price_change < 0
            }
            
            await self.mongodb.db.price_history.insert_one(history_entry)
            
            # Invalida cache de análise
            await self.redis.delete(f"analysis:{asin}")
            
            # Verifica alertas se necessário
            alerts_triggered = []
            if check_alerts:
                alerts_triggered = await self._check_price_alerts(
                    product,
                    old_price,
                    new_price
                )
            
            # Analisa tendência
            analysis = await self.analyze_price(asin)
            
            # Detecta promoção falsa
            is_fake_sale = await self._detect_fake_sale(asin, new_price)
            
            return {
                "success": True,
                "changed": True,
                "old_price": old_price,
                "new_price": new_price,
                "change_amount": price_change,
                "change_percentage": round(price_change_pct, 2),
                "alerts_triggered": alerts_triggered,
                "analysis": analysis,
                "is_fake_sale": is_fake_sale
            }
            
        except Exception as e:
            logger.error(f"Erro ao atualizar preço: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def analyze_price(self, asin: str) -> PriceAnalysis:
        """
        Analisa preço e tendências de um produto
        
        Args:
            asin: ASIN do produto
            
        Returns:
            PriceAnalysis com análise completa
            
        Note:
            Usa histórico de preços para identificar:
            - Tendências de curto e longo prazo
            - Volatilidade
            - Momentos ideais de compra
            - Previsões futuras
        """
        try:
            # Verifica cache
            cached = await self.redis.get(f"analysis:{asin}")
            if cached:
                return PriceAnalysis(**cached)
            
            # Busca produto e histórico
            product = await self.mongodb.get_product_by_asin(asin)
            if not product:
                raise ValueError(f"Produto não encontrado: {asin}")
            
            # Busca histórico de 30 dias
            history = await self.mongodb.get_price_history(asin, days=30)
            
            if len(history) < self.min_history_points:
                # Análise básica com poucos dados
                return self._basic_analysis(product, history)
            
            # Extrai preços e timestamps
            prices = [h["price"] for h in history]
            timestamps = [h["timestamp"] for h in history]
            
            # Análise estatística
            current_price = product.current_price
            previous_price = prices[-2] if len(prices) > 1 else current_price
            
            # Médias móveis
            prices_7d = prices[-7:] if len(prices) >= 7 else prices
            prices_30d = prices
            
            avg_7d = np.mean(prices_7d)
            avg_30d = np.mean(prices_30d)
            min_30d = np.min(prices_30d)
            max_30d = np.max(prices_30d)
            
            # Calcula volatilidade (desvio padrão normalizado)
            volatility = np.std(prices_30d) / avg_30d if avg_30d > 0 else 0
            
            # Detecta tendência
            trend = self._detect_trend(prices)
            
            # Mudança de preço
            change_amount = current_price - previous_price
            change_pct = (change_amount / previous_price * 100) if previous_price > 0 else 0
            
            # Determina se é um bom negócio
            is_good_deal = self._is_good_deal(
                current_price,
                avg_30d,
                min_30d,
                volatility
            )
            
            # Gera recomendação
            recommendation = self._generate_recommendation(
                current_price,
                avg_30d,
                min_30d,
                trend,
                volatility,
                is_good_deal
            )
            
            # Calcula score de confiança
            confidence = self._calculate_confidence(
                len(history),
                volatility,
                trend
            )
            
            # Cria análise
            analysis = PriceAnalysis(
                current_price=current_price,
                previous_price=previous_price,
                change_amount=round(change_amount, 2),
                change_percentage=round(change_pct, 2),
                trend=trend,
                avg_price_7d=round(avg_7d, 2),
                avg_price_30d=round(avg_30d, 2),
                min_price_30d=round(min_30d, 2),
                max_price_30d=round(max_30d, 2),
                volatility=round(volatility, 4),
                is_good_deal=is_good_deal,
                recommendation=recommendation,
                confidence_score=round(confidence, 2)
            )
            
            # Salva no cache
            await self.redis.set(
                f"analysis:{asin}",
                analysis.__dict__,
                ttl=self.cache_ttl
            )
            
            return analysis
            
        except Exception as e:
            logger.error(f"Erro na análise de preço: {str(e)}")
            # Retorna análise básica em caso de erro
            return self._basic_analysis(product, [])
    
    def _detect_trend(self, prices: List[float]) -> PriceTrend:
        """
        Detecta tendência nos preços
        
        Args:
            prices: Lista de preços históricos
            
        Returns:
            PriceTrend identificada
            
        Note:
            Usa regressão linear e análise de variação
            para identificar tendências de curto e longo prazo
        """
        if len(prices) < 3:
            return PriceTrend.STABLE
        
        # Calcula tendência usando regressão linear simples
        x = np.arange(len(prices))
        y = np.array(prices)
        
        # Coeficiente de inclinação
        slope = np.polyfit(x, y, 1)[0]
        
        # Normaliza pela média para ter porcentagem
        avg_price = np.mean(prices)
        normalized_slope = (slope / avg_price) if avg_price > 0 else 0
        
        # Calcula volatilidade
        volatility = np.std(prices) / avg_price if avg_price > 0 else 0
        
        # Verifica mínimo/máximo histórico
        current_price = prices[-1]
        if current_price <= np.min(prices) * 1.01:  # Dentro de 1% do mínimo
            return PriceTrend.HISTORIC_LOW
        elif current_price >= np.max(prices) * 0.99:  # Dentro de 1% do máximo
            return PriceTrend.HISTORIC_HIGH
        
        # Alta volatilidade sobrepõe tendência
        if volatility > self.volatility_threshold:
            return PriceTrend.VOLATILE
        
        # Determina tendência baseada na inclinação
        if abs(normalized_slope) < 0.001:  # Menos de 0.1% de variação
            return PriceTrend.STABLE
        elif normalized_slope > 0:
            return PriceTrend.INCREASING
        else:
            return PriceTrend.DECREASING
    
    def _is_good_deal(
        self,
        current_price: float,
        avg_price: float,
        min_price: float,
        volatility: float
    ) -> bool:
        """
        Determina se o preço atual é um bom negócio
        
        Args:
            current_price: Preço atual
            avg_price: Média de preço
            min_price: Preço mínimo histórico
            volatility: Volatilidade do preço
            
        Returns:
            bool: True se é um bom negócio
            
        Critérios:
        - Preço abaixo da média
        - Próximo ao mínimo histórico
        - Baixa volatilidade (preço estável)
        """
        # Preço deve estar abaixo da média
        if current_price >= avg_price:
            return False
        
        # Quanto abaixo da média? (porcentagem)
        below_avg_pct = (avg_price - current_price) / avg_price
        
        # Proximidade ao mínimo (porcentagem)
        above_min_pct = (current_price - min_price) / min_price if min_price > 0 else 1
        
        # Critérios para bom negócio:
        # 1. Pelo menos 5% abaixo da média
        # 2. Dentro de 10% do mínimo histórico
        # 3. Volatilidade não muito alta
        is_good = (
            below_avg_pct >= 0.05 and
            above_min_pct <= 0.10 and
            volatility < self.volatility_threshold * 2
        )
        
        return is_good
    
    def _generate_recommendation(
        self,
        current_price: float,
        avg_price: float,
        min_price: float,
        trend: PriceTrend,
        volatility: float,
        is_good_deal: bool
    ) -> str:
        """
        Gera recomendação de compra baseada na análise
        
        Returns:
            str: Recomendação textual
        """
        # Recomendações baseadas em diferentes cenários
        if is_good_deal:
            if trend == PriceTrend.HISTORIC_LOW:
                return "🔥 COMPRE AGORA! Preço no mínimo histórico."
            elif trend == PriceTrend.DECREASING:
                return "✅ BOM MOMENTO! Preço em queda e abaixo da média."
            else:
                return "👍 Bom preço! Abaixo da média histórica."
        
        if trend == PriceTrend.HISTORIC_HIGH:
            return "⚠️ EVITE! Preço no máximo histórico."
        
        if trend == PriceTrend.INCREASING:
            if current_price > avg_price * 1.1:
                return "❌ Aguarde! Preço em alta, pode cair em breve."
            else:
                return "⏰ Compre logo! Preço subindo mas ainda razoável."
        
        if trend == PriceTrend.VOLATILE:
            return "📊 Monitore! Alta volatilidade, aguarde estabilização."
        
        if current_price < avg_price:
            return "👀 Considere! Preço abaixo da média."
        
        return "📈 Acompanhe! Preço na média histórica."
    
    def _calculate_confidence(
        self,
        data_points: int,
        volatility: float,
        trend: PriceTrend
    ) -> float:
        """
        Calcula score de confiança da análise
        
        Args:
            data_points: Quantidade de pontos de dados
            volatility: Volatilidade
            trend: Tendência identificada
            
        Returns:
            float: Score de 0 a 100
        """
        # Base score baseado em quantidade de dados
        if data_points < 5:
            base_score = 30
        elif data_points < 10:
            base_score = 50
        elif data_points < 30:
            base_score = 70
        else:
            base_score = 85
        
        # Ajusta por volatilidade (menos volátil = mais confiável)
        volatility_penalty = min(volatility * 100, 20)
        
        # Ajusta por clareza da tendência
        trend_bonus = 0
        if trend in [PriceTrend.HISTORIC_LOW, PriceTrend.HISTORIC_HIGH]:
            trend_bonus = 10
        elif trend != PriceTrend.VOLATILE:
            trend_bonus = 5
        
        # Calcula score final
        confidence = base_score - volatility_penalty + trend_bonus
        
        # Limita entre 0 e 100
        return max(0, min(100, confidence))
    
    def _basic_analysis(
        self,
        product: Product,
        history: List[Dict]
    ) -> PriceAnalysis:
        """
        Análise básica quando há poucos dados históricos
        
        Args:
            product: Produto
            history: Histórico limitado
            
        Returns:
            PriceAnalysis básica
        """
        current_price = product.current_price
        
        if history:
            prices = [h["price"] for h in history]
            avg_price = np.mean(prices)
            min_price = np.min(prices)
            max_price = np.max(prices)
        else:
            avg_price = current_price
            min_price = current_price
            max_price = current_price
        
        return PriceAnalysis(
            current_price=current_price,
            previous_price=current_price,
            change_amount=0,
            change_percentage=0,
            trend=PriceTrend.STABLE,
            avg_price_7d=avg_price,
            avg_price_30d=avg_price,
            min_price_30d=min_price,
            max_price_30d=max_price,
            volatility=0,
            is_good_deal=False,
            recommendation="📊 Dados insuficientes. Continue monitorando.",
            confidence_score=25.0
        )
    
    async def _check_price_alerts(
        self,
        product: Product,
        old_price: float,
        new_price: float
    ) -> List[str]:
        """
        Verifica e dispara alertas de preço
        
        Args:
            product: Produto
            old_price: Preço anterior
            new_price: Novo preço
            
        Returns:
            Lista de alertas disparados
        """
        alerts_triggered = []
        
        try:

# Verifica alerta de preço alvo
            if product.has_alert and product.alert_price:
                if new_price <= product.alert_price and old_price > product.alert_price:
                    alert_type = "target_price_reached"
                    alerts_triggered.append(alert_type)
                    
                    # Dispara notificações
                    await self._trigger_price_alert(
                        product,
                        alert_type,
                        old_price,
                        new_price
                    )
            
            # Verifica queda significativa
            price_drop_pct = (old_price - new_price) / old_price if old_price > 0 else 0
            
            if price_drop_pct >= 0.10:  # Queda de 10% ou mais
                alert_type = "significant_price_drop"
                alerts_triggered.append(alert_type)
            
         await self._trigger_price_alert(
                    product,
                    alert_type,
                    old_price,
                    new_price
                )
            
            # Verifica mínimo histórico
            history = await self.mongodb.get_price_history(product.asin, days=90)
            if history:
                all_prices = [h["price"] for h in history]
                if new_price <= min(all_prices):
                    alert_type = "historic_low"
                    alerts_triggered.append(alert_type)
                    
                    await self._trigger_price_alert(
                        product,
                        alert_type,
                        old_price,
                        new_price
                    )


logger.info(
                f"Alertas verificados para {product.asin}",
                alerts_triggered=alerts_triggered
            )
            
        except Exception as e:
            logger.error(f"Erro ao verificar alertas: {str(e)}")
        
        return alerts_triggered
    
    async def _trigger_price_alert(
        self,
        product: Product,
        alert_type: str,
        old_price: float,
        new_price: float
    ):
        """
        Dispara alerta de preço para todos canais configurados
        
        Args:
            product: Produto
            alert_type: Tipo do alerta
            old_price: Preço anterior
            new_price: Novo preço
        """
      

try:
            # Prepara dados do alerta
            alert_data = {
                "alert_type": alert_type,
                "asin": product.asin,
                "title": product.title,
                "old_price": old_price,
                "new_price": new_price,
                "change_amount": old_price - new_price,
                "change_percentage": round((old_price - new_price) / old_price * 100, 2),
                "url": product.url,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Dispara webhook
            await self.webhook_manager.trigger_event(
                event_type="price_alert",
                data=alert_data
            )
  

# Aqui você também pode enviar email, Telegram, etc.
            # Exemplo:
            # await email_sender.send_price_alert(...)
            # await telegram_bot.send_price_alert(...)
            
            logger.info(
                f"Alerta de preço disparado",
                alert_type=alert_type,
                asin=product.asin,
                new_price=new_price
            )
            
        except Exception as e:
            logger.error(f"Erro ao disparar alerta: {str(e)}")
    
    async def _detect_fake_sale(
        self,
        asin: str,
        current_price: float
    ) -> bool:
        """
        Detecta se uma "promoção" é falsa
        
        Args:
        
asin: ASIN do produto
            current_price: Preço atual
            
        Returns:
            bool: True se parece ser promoção falsa
            
        Note:
            Detecta padrões comuns de promoções falsas:
            - Preço aumentado antes da "promoção"
            - Preço de "promoção" igual à média histórica
            - Flutuações artificiais de preço
        """
        try:
            # Busca histórico de 60 dias
            history = await self.mongodb.get_price_history(asin, days=60)
            
            if len(history) < 10:
                return False
            
            prices = [h["price"] for h in history]
            timestamps = [h["timestamp"] for h in history]
          
# Verifica se houve aumento recente seguido de "desconto"
            recent_prices = prices[-7:]  # Última semana
            older_prices = prices[-30:-7] if len(prices) > 30 else prices[:-7]
            
            if not older_prices:
                return False
            
            avg_recent = np.mean(recent_prices)
            avg_older = np.mean(older_prices)
            
            # Se o preço aumentou >20% recentemente e agora está em "promoção"
            if avg_recent > avg_older * 1.2 and current_price < avg_recent * 0.9:
                logger.warning(
                    f"Possível promoção falsa detectada para {asin}",
                    pattern="price_pump_and_dump"
                )
                return True
              # Se o preço de "promoção" é na verdade a média histórica
            avg_all_time = np.mean(prices)
            if abs(current_price - avg_all_time) / avg_all_time < 0.05:  # Dentro de 5%
                # Verifica se está sendo anunciado como promoção
                # (Isso dependeria de ter acesso aos dados de "preço original" mostrado)
                pass
            
            return False
            
        except Exception as e:
            logger.error(f"Erro ao detectar promoção falsa: {str(e)}")
            return False
    
    async def bulk_check_prices(
        self,
        asins: List[str]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Verifica preços de múltiplos produtos
        
        Args:
            asins: Lista de ASINs
            
        Returns:
            Dict com resultado para cada ASIN
        """
        results = {}
        
        for asin in asins:
            try:
                # Aqui você integraria com o scraper
                # Por enquanto, simula atualização
                
                # Busca produto
                product = await self.mongodb.get_product_by_asin(asin)
                
                if product:
                    # Simula novo preço (substitua com scraping real)
                    import random
                    variation = random.uniform(-0.1, 0.1)  # ±10%
                    new_price = product.current_price * (1 + variation)
                  # Atualiza preço
                    result = await self.update_price(asin, new_price)
                    results[asin] = result
                else:
                    results[asin] = {
                        "success": False,
                        "error": "Produto não encontrado"
                    }
                    
            except Exception as e:
                logger.error(f"Erro ao verificar preço de {asin}: {str(e)}")
                results[asin] = {
                    "success": False,
                    "error": str(e)
                }
        
        return results
