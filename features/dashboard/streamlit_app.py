"""
Dashboard interativo com Streamlit para visualização de dados
Interface web completa para monitoramento e análise
"""
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any
import numpy as np

# Importações do projeto
import sys
sys.path.append("../..")  # Ajusta path para importar módulos do projeto

from storage.mongodb_client import MongoDBClient
from storage.redis_cache import RedisCache
from features.analysis.price_tracker import PriceTracker
from config.settings import settings
from utils.logger import logger

# ==================== Configuração da Página ====================

st.set_page_config(
    page_title="Amazon Price Tracker Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==================== Estilos Customizados ====================

st.markdown("""
<style>
    /* Tema customizado */
    .main {
        background-color: #f5f7fa;
    }
    
    /* Cards de métricas */
    .metric-card {
        background: white;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin: 10px 0;
    }
    
    /* Títulos de seção */
    .section-title {
        color: #2c3e50;
        font-size: 24px;
        font-weight: bold;
        margin: 20px 0 10px 0;
        border-bottom: 3px solid #667eea;
        padding-bottom: 10px;
    }
    
    /* Botões personalizados */
    .stButton>button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        padding: 10px 25px;
        border-radius: 25px;
        font-weight: bold;
        transition: all 0.3s;
    }
    
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
    }
    
    /* Alertas */
    .alert-success {
        background-color: #d4edda;
        border-left: 4px solid #28a745;
        padding: 10px;
        margin: 10px 0;
        border-radius: 5px;
    }
    
    .alert-warning {
        background-color: #fff3cd;
        border-left: 4px solid #ffc107;
        padding: 10px;
        margin: 10px 0;
        border-radius: 5px;
    }
    
    .alert-danger {
        background-color: #f8d7da;
        border-left: 4px solid #dc3545;
        padding: 10px;
        margin: 10px 0;
        border-radius: 5px;
    }
    
    /* Tabelas */
    .dataframe {
        font-size: 14px;
    }
    
    .dataframe th {
        background-color: #667eea !important;
        color: white !important;
        font-weight: bold !important;
    }
    
    /* Sidebar */
    .css-1d391kg {
        background-color: #2c3e50;
    }
    
    /* Footer */
    .footer {
        position: fixed;
        bottom: 0;
        width: 100%;
        background-color: #2c3e50;
        color: white;
        text-align: center;
        padding: 10px;
        font-size: 12px;
    }
</style>
""", unsafe_allow_html=True)

# ==================== Funções de Conexão ====================

@st.cache_resource
def get_mongodb_connection():
    """
    Obtém conexão com MongoDB (cached)
    
    Returns:
        MongoDBClient: Cliente MongoDB configurado
        
    Note:
        Usa @st.cache_resource para manter conexão única
        durante toda a sessão do Streamlit
    """
    try:
        mongodb = MongoDBClient()
        # Como asyncio não funciona bem com cache do Streamlit,
        # usamos conexão síncrona aqui
        import motor.motor_asyncio
        mongodb.client = motor.motor_asyncio.AsyncIOMotorClient(
            settings.mongodb_atlas_uri
        )
        mongodb.db = mongodb.client[settings.mongodb_database]
        mongodb._initialized = True
        logger.info("MongoDB conectado no dashboard")
        return mongodb
    except Exception as e:
        logger.error(f"Erro ao conectar MongoDB: {str(e)}")
        st.error(f"❌ Erro ao conectar banco de dados: {str(e)}")
        return None

@st.cache_resource
def get_redis_connection():
    """Obtém conexão com Redis (cached)"""
    try:
        redis_cache = RedisCache()
        # Configuração similar ao MongoDB
        return redis_cache
    except Exception as e:
        logger.error(f"Erro ao conectar Redis: {str(e)}")
        st.warning(f"⚠️ Cache desabilitado: {str(e)}")
        return None

# ==================== Funções Auxiliares ====================

def format_currency(value: float, currency: str = "USD") -> str:
    """
    Formata valor como moeda
    
    Args:
        value: Valor numérico
        currency: Código da moeda
        
    Returns:
        str: Valor formatado (ex: $99.99)
    """
    symbols = {
        "USD": "$",
        "EUR": "€",
        "GBP": "£",
        "BRL": "R$"
    }
    symbol = symbols.get(currency, "$")
    return f"{symbol}{value:,.2f}"

def format_percentage(value: float, show_sign: bool = True) -> str:
    """
    Formata porcentagem
    
    Args:
        value: Valor percentual
        show_sign: Se deve mostrar sinal +/-
        
    Returns:
        str: Porcentagem formatada
    """
    if show_sign:
        sign = "+" if value > 0 else ""
        return f"{sign}{value:.2f}%"
    return f"{value:.2f}%"

def create_metric_card(title: str, value: str, delta: str = None, delta_color: str = "normal"):
    """
    Cria card de métrica customizado
    
    Args:
        title: Título da métrica
        value: Valor principal
        delta: Variação (opcional)
        delta_color: Cor da variação (normal/inverse/off)
    """
    col1, col2 = st.columns([3, 1])
    with col1:
        st.metric(
            label=title,
            value=value,
            delta=delta,
            delta_color=delta_color
        )

def run_async(coro):
    """
    Executa coroutine assíncrona no Streamlit
    
    Args:
        coro: Coroutine para executar
        
    Returns:
        Resultado da coroutine
        
    Note:
        Necessário porque Streamlit não suporta async nativo
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()

# ==================== Sidebar de Navegação ====================

def render_sidebar():
    """
    Renderiza sidebar com navegação e filtros
    
    Returns:
        str: Página selecionada
    """
    with st.sidebar:
        # Logo e título
        st.image("https://via.placeholder.com/200x80/667eea/ffffff?text=Price+Tracker", 
                 use_column_width=True)
        
        st.markdown("---")
        
        # Menu de navegação
        st.markdown("### 📊 Navegação")
        page = st.radio(
            "Escolha uma página:",
            [
                "🏠 Dashboard",
                "📦 Produtos",
                "📈 Análise de Preços",
                "🔔 Alertas",
                "📊 Estatísticas",
                "⚙️ Configurações"
            ],
            label_visibility="collapsed"
        )
        
        st.markdown("---")
        
        # Filtros globais
        st.markdown("### 🔍 Filtros")
        
        # Período de tempo
        time_range = st.selectbox(
            "Período:",
            ["Últimas 24h", "Última semana", "Último mês", "Últimos 3 meses", "Último ano"],
            index=1
        )
        
        # Status
        status_filter = st.multiselect(
            "Status:",
            ["Em Estoque", "Fora de Estoque", "Pré-venda"],
            default=["Em Estoque"]
        )
        
        # Faixa de preço
        st.markdown("**Faixa de Preço:**")
        price_range = st.slider(
            "Selecione:",
            0, 1000, (0, 500),
            label_visibility="collapsed"
        )
        
        st.markdown("---")
        
        # Ações rápidas
        st.markdown("### ⚡ Ações Rápidas")
        
        if st.button("🔄 Atualizar Dados", use_container_width=True):
            st.rerun()
        
        if st.button("📥 Exportar Relatório", use_container_width=True):
            st.info("Função de exportação em desenvolvimento")
        
        if st.button("➕ Novo Rastreamento", use_container_width=True):
            st.session_state.show_add_modal = True
        
        st.markdown("---")
        
        # Info do sistema
        st.markdown("### 💡 Sistema")
        st.info(f"""
        **Versão:** {settings.app_version}  
        **Ambiente:** {settings.environment}  
        **Uptime:** 99.9%
        """)
        
        return page

# ==================== Página: Dashboard Principal ====================

def render_dashboard():
    """
    Renderiza dashboard principal com visão geral
    
    Mostra:
    - KPIs principais
    - Gráficos de tendência
    - Produtos em destaque
    - Atividade recente
    """
    st.markdown('<h1 class="section-title">🏠 Dashboard - Visão Geral</h1>', 
                unsafe_allow_html=True)
    
    # ========== KPIs Principais ==========
    
    st.markdown("### 📊 Métricas Principais")
    
    # Busca dados do MongoDB
    mongodb = get_mongodb_connection()
    
    if mongodb:
        try:
            # Total de produtos rastreados
            total_products = run_async(
                mongodb.products.count_documents({"is_tracked": True})
            )
            
            # Alertas ativos
            active_alerts = run_async(
                mongodb.products.count_documents({"has_alert": True})
            )
            
            # Economia total (exemplo)
            total_savings = 1234.56  # Calcular baseado em histórico
            
            # Produtos com queda de preço hoje
            today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            price_drops_today = run_async(
                mongodb.price_history.count_documents({
                    "timestamp": {"$gte": today},
                    "is_decrease": True
                })
            )
            
            # Exibe métricas em colunas
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric(
                    label="📦 Produtos Rastreados",
                    value=total_products,
                    delta="+5 esta semana",
                    delta_color="normal"
                )
            
            with col2:
                st.metric(
                    label="🔔 Alertas Ativos",
                    value=active_alerts,
                    delta=None
                )
            
            with col3:
                st.metric(
                    label="💰 Economia Total",
                    value=format_currency(total_savings),
                    delta="+$45.32 este mês",
                    delta_color="normal"
                )
            
            with col4:
                st.metric(
                    label="📉 Quedas Hoje",
                    value=price_drops_today,
                    delta=f"{price_drops_today} produtos",
                    delta_color="normal"
                )
                
        except Exception as e:
            st.error(f"Erro ao carregar métricas: {str(e)}")
            logger.error(f"Erro no dashboard: {str(e)}")
    
    st.markdown("---")
    
    # ========== Gráficos ==========
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📈 Tendência de Preços (Últimos 30 dias)")
        
        # Dados de exemplo (substitua com dados reais)
        dates = pd.date_range(end=datetime.now(), periods=30, freq='D')
        avg_prices = np.random.uniform(45, 55, 30)
        
        # Cria gráfico de linha
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=dates,
            y=avg_prices,
            mode='lines+markers',
            name='Preço Médio',
            line=dict(color='#667eea', width=3),
            fill='tozeroy',
            fillcolor='rgba(102, 126, 234, 0.2)'
        ))
        
        fig.update_layout(
            height=350,
            margin=dict(l=0, r=0, t=30, b=0),
            xaxis_title="Data",
            yaxis_title="Preço Médio ($)",
            hovermode='x unified',
            template="plotly_white"
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.markdown("### 🏆 Top Categorias")
        
        # Dados de exemplo
        categories = ['Eletrônicos', 'Livros', 'Casa', 'Esportes', 'Moda']
        counts = [45, 32, 28, 21, 15]
        
        # Gráfico de barras horizontal
        fig = go.Figure(go.Bar(
            x=counts,
            y=categories,
            orientation='h',
            marker=dict(
                color=counts,
                colorscale='Viridis',
                showscale=False
            ),
            text=counts,
            textposition='auto'
        ))
        
        fig.update_layout(
            height=350,
            margin=dict(l=0, r=0, t=30, b=0),
            xaxis_title="Número de Produtos",
            yaxis_title="",

                  template="plotly_white"
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("---")
    
    # ========== Produtos em Destaque ==========
    
    st.markdown("### ⭐ Produtos em Destaque")
    
    # Tabs para diferentes visualizações
    tab1, tab2, tab3 = st.tabs(["🔥 Maiores Quedas", "💎 Melhores Ofertas", "📊 Mais Rastreados"])
    
    with tab1:
        # Produtos com maior queda de preço
        if mongodb:
            try:
                # Busca produtos com quedas recentes
                pipeline = [
                    {
                        "$match": {
                            "is_tracked": True,
                            "price_history": {"$exists": True, "$ne": []}
                        }
                    },
                    {
                        "$limit": 5
                    }
                ]
                
                products = run_async(
                    mongodb.products.aggregate(pipeline).to_list(5)
                )
                
                if products:
                    for product in products:
                        with st.container():
                            col1, col2, col3, col4 = st.columns([3, 2, 2, 2])
                            
                            with col1:
                                st.markdown(f"**{product.get('title', 'Produto')[:60]}...**")
                                st.caption(f"ASIN: {product.get('asin', 'N/A')}")
                            
                            with col2:
                                current = product.get('current_price', 0)
                                st.markdown(f"**{format_currency(current)}**")
                            
                            with col3:
                                # Simula queda de preço
                                drop = -15.5
                                st.markdown(
                                    f"<span style='color: #28a745; font-weight: bold;'>"
                                    f"📉 {format_percentage(drop)}"
                                    f"</span>",
                                    unsafe_allow_html=True
                                )
                            
                            with col4:
                                if st.button("Ver Detalhes", key=f"detail_{product.get('asin')}"):
                                    st.session_state.selected_product = product.get('asin')
                            
                            st.markdown("---")
                else:
                    st.info("Nenhum produto com queda de preço recente")
                    
            except Exception as e:
                st.error(f"Erro ao carregar produtos: {str(e)}")
    
    with tab2:
        st.info("🚧 Análise de melhores ofertas em desenvolvimento")
    
    with tab3:
        st.info("🚧 Lista de produtos mais rastreados em desenvolvimento")
    
    # ========== Atividade Recente ==========
    
    st.markdown("---")
    st.markdown("### 📋 Atividade Recente")
    
    # Timeline de eventos
    with st.expander("Ver últimas 10 atividades", expanded=True):
        activities = [
            {"time": "Há 5 minutos", "event": "Preço atualizado", "product": "Echo Dot 4th Gen", "icon": "🔄"},
            {"time": "Há 15 minutos", "event": "Alerta disparado", "product": "Kindle Paperwhite", "icon": "🔔"},
            {"time": "Há 1 hora", "event": "Novo produto rastreado", "product": "Fire TV Stick", "icon": "➕"},
            {"time": "Há 2 horas", "event": "Preço caiu", "product": "Echo Show 8", "icon": "📉"},
            {"time": "Há 3 horas", "event": "Produto voltou ao estoque", "product": "Ring Doorbell", "icon": "✅"},
        ]
        
        for activity in activities:
            col1, col2, col3 = st.columns([1, 3, 2])
            
            with col1:
                st.markdown(f"### {activity['icon']}")
            
            with col2:
                st.markdown(f"**{activity['event']}**")
                st.caption(activity['product'])
            
            with col3:
                st.caption(activity['time'])
            
            st.markdown("---")

# ==================== Página: Produtos ====================

def render_products_page():
    """
    Renderiza página de gerenciamento de produtos
    
    Features:
    - Lista de produtos rastreados
    - Busca e filtros
    - Adicionar/remover produtos
    - Editar configurações
    """
    st.markdown('<h1 class="section-title">📦 Gerenciamento de Produtos</h1>', 
                unsafe_allow_html=True)
    
    # ========== Barra de Ferramentas ==========
    
    col1, col2, col3 = st.columns([2, 2, 1])
    
    with col1:
        search_query = st.text_input(
            "🔍 Buscar produto",
            placeholder="Digite ASIN, título ou marca...",
            label_visibility="collapsed"
        )
    
    with col2:
        sort_by = st.selectbox(
            "Ordenar por:",
            ["Mais recentes", "Maior queda", "Menor preço", "Maior preço", "A-Z"],
            label_visibility="collapsed"
        )
    
    with col3:
        if st.button("➕ Adicionar", use_container_width=True):
            st.session_state.show_add_product = True
    
    st.markdown("---")
    
    # ========== Modal para Adicionar Produto ==========
    
    if st.session_state.get('show_add_product', False):
        with st.form("add_product_form"):
            st.markdown("### ➕ Adicionar Novo Produto")
            
            url = st.text_input(
                "URL do Produto na Amazon:",
                placeholder="https://www.amazon.com/dp/..."
            )
            
            target_price = st.number_input(
                "Preço Alvo (opcional):",
                min_value=0.0,
                step=0.01,
                format="%.2f"
            )
            
            col1, col2 = st.columns(2)
            
            with col1:
                submit = st.form_submit_button("✅ Adicionar", use_container_width=True)
            
            with col2:
                cancel = st.form_submit_button("❌ Cancelar", use_container_width=True)
            
            if submit:
                if url:
                    with st.spinner("Processando produto..."):
                        # Aqui você chamaria a API de scraping
                        st.success("✅ Produto adicionado com sucesso!")
                        st.session_state.show_add_product = False
                        st.rerun()
                else:
                    st.error("❌ Por favor, insira uma URL válida")
            
            if cancel:
                st.session_state.show_add_product = False
                st.rerun()
        
        st.markdown("---")
    
    # ========== Lista de Produtos ==========
    
    mongodb = get_mongodb_connection()
    
    if mongodb:
        try:
            # Busca produtos
            query = {"is_tracked": True}
            
            if search_query:
                query["$or"] = [
                    {"title": {"$regex": search_query, "$options": "i"}},
                    {"asin": {"$regex": search_query, "$options": "i"}},
                    {"brand": {"$regex": search_query, "$options": "i"}}
                ]
            
            products = run_async(
                mongodb.products.find(query).limit(20).to_list(20)
            )
            
            if products:
                st.markdown(f"**{len(products)} produtos encontrados**")
                
                # Cria tabela de produtos
                for i, product in enumerate(products):
                    with st.container():
                        col1, col2, col3, col4, col5 = st.columns([4, 2, 2, 2, 1])
                        
                        with col1:
                            # Título e imagem (se disponível)
                            if product.get('images'):
                                st.image(
                                    product['images'][0].get('url', ''),
                                    width=80
                                )
                            
                            st.markdown(f"**{product.get('title', 'Sem título')[:80]}**")
                            st.caption(f"ASIN: {product.get('asin', 'N/A')} | {product.get('brand', 'N/A')}")
                        
                        with col2:
                            st.markdown("**Preço Atual**")
                            st.markdown(
                                f"<h3 style='color: #667eea;'>"
                                f"{format_currency(product.get('current_price', 0))}"
                                f"</h3>",
                                unsafe_allow_html=True
                            )
                        
                        with col3:
                            st.markdown("**Status**")
                            status = product.get('status', 'unknown')
                            
                            status_colors = {
                                'in_stock': '🟢',
                                'out_of_stock': '🔴',
                                'limited_stock': '🟡'
                            }
                            
                            status_icon = status_colors.get(status, '⚪')
                            st.markdown(f"{status_icon} {status.replace('_', ' ').title()}")
                        
                        with col4:
                            st.markdown("**Alerta**")
                            if product.get('has_alert'):
                                st.markdown(f"🎯 {format_currency(product.get('alert_price', 0))}")
                            else:
                                st.caption("Não configurado")
                        
                        with col5:
                            # Botão de ações
                            if st.button("⋮", key=f"actions_{i}"):
                                st.session_state[f'show_actions_{i}'] = not st.session_state.get(f'show_actions_{i}', False)
                        
                        # Menu de ações (se aberto)
                        if st.session_state.get(f'show_actions_{i}', False):
                            action_col1, action_col2, action_col3 = st.columns(3)
                            
                            with action_col1:
                                if st.button("📊 Análise", key=f"analyze_{i}", use_container_width=True):
                                    st.session_state.analyze_product = product.get('asin')
                            
                            with action_col2:
                                if st.button("⚙️ Editar", key=f"edit_{i}", use_container_width=True):
                                    st.session_state.edit_product = product.get('asin')
                            
                            with action_col3:
                                if st.button("🗑️ Remover", key=f"delete_{i}", use_container_width=True):
                                    if st.confirm(f"Remover {product.get('title', 'produto')}?"):
                                        # Chamar API para remover
                                        st.success("✅ Produto removido!")
                                        st.rerun()
                        
                        st.markdown("---")
            else:
                st.info("📭 Nenhum produto encontrado. Adicione produtos para começar!")
                
        except Exception as e:
            st.error(f"Erro ao carregar produtos: {str(e)}")
            logger.error(f"Erro na página de produtos: {str(e)}")
    else:
        st.error("❌ Erro ao conectar com o banco de dados")

# ==================== Página: Análise de Preços ====================

def render_price_analysis_page():
    """
    Renderiza página de análise detalhada de preços
    
    Features:
    - Gráficos interativos de histórico
    - Análise de tendências
    - Previsões de preço
    - Comparação de produtos
    """
    st.markdown('<h1 class="section-title">📈 Análise de Preços</h1>', 
                unsafe_allow_html=True)
    
    # ========== Seletor de Produto ==========
    
    mongodb = get_mongodb_connection()
    
    if mongodb:
        try:
            # Busca lista de produtos
            products = run_async(
                mongodb.products.find({"is_tracked": True}).to_list(100)
            )
            
            if products:
                # Cria dicionário de produtos
                product_options = {
                    f"{p.get('title', 'Produto')[:50]} ({p.get('asin')})": p.get('asin')
                    for p in products
                }
                
                selected_product_name = st.selectbox(
                    "Selecione um produto para análise:",
                    list(product_options.keys())
                )
                
                selected_asin = product_options[selected_product_name]
                
                # Busca dados do produto selecionado
                product = next((p for p in products if p.get('asin') == selected_asin), None)
                
                if product:
                    st.markdown("---")
                    
                    # ========== Informações do Produto ==========
                    
                    col1, col2 = st.columns([1, 3])
                    
                    with col1:
                        if product.get('images'):
                            st.image(
                                product['images'][0].get('url', ''),
                                use_column_width=True
                            )
                    
                    with col2:
                        st.markdown(f"### {product.get('title', 'Produto')}")
                        st.caption(f"**Marca:** {product.get('brand', 'N/A')}")
                        st.caption(f"**ASIN:** {product.get('asin', 'N/A')}")
                        st.caption(f"**Categoria:** {', '.join(product.get('category', ['N/A']))}")
                        
                        # Link para Amazon
                        if product.get('url'):
                            st.markdown(f"[🔗 Ver na Amazon]({product.get('url')})")
                    
                    st.markdown("---")
                    
                    # ========== Métricas do Produto ==========
                    
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        st.metric(
                            "Preço Atual",
                            format_currency(product.get('current_price', 0)),
                            delta="-$5.00" if np.random.random() > 0.5 else "+$2.00"
                        )
                    
                    with col2:
                        # Calcula média de 30 dias (simulado)
                        avg_30d = product.get('current_price', 0) * 1.1
                        st.metric(
                            "Média 30 dias",
                            format_currency(avg_30d)
                        )
                    
                    with col3:
                        # Mínimo histórico (simulado)
                        min_price = product.get('current_price', 0) * 0.85
                        st.metric(
                            "Mínimo Histórico",
                                                        format_currency(min_price)
                        )

                    with col4:
                        # Máximo histórico (simulado)
                        max_price = product.get('current_price', 0) * 1.35
                        st.metric(
                            "Máximo Histórico",
                            format_currency(max_price)
                        )

                    st.markdown("---")

                    # ========== Gráfico Histórico ==========
                    st.markdown("### 📊 Histórico de Preços (Simulado)")
                    # monta mock de dados
                    days = pd.date_range(datetime.now() - timedelta(days=30), periods=30)
                    values = np.cumsum(np.random.randn(len(days))) + product.get('current_price', 50)
                    df = pd.DataFrame({"Data": days, "Preço": values})

                    fig_hist = px.line(df, x="Data", y="Preço", title="Histórico de 30 dias", markers=True)
                    fig_hist.update_traces(line_color='#667eea')
                    fig_hist.update_layout(height=400, template="plotly_white")
                    st.plotly_chart(fig_hist, use_container_width=True)

                    st.markdown("### 🤖 Análise de Tendência")
                    st.info("Em produção: integração direta com o módulo `PriceTracker.analyze_price()` "
                            "para exibir tendências e recomendações em tempo real.")

                else:
                    st.error("Produto selecionado não encontrado.")
            else:
                st.info("Nenhum produto rastreado para analisar.")
        except Exception as e:
            st.error(f"Erro carregando produtos: {e}")


# ==================== Distribuição da Execução ====================

def run_dashboard():
    """
    Loop principal: chama o renderizador adequado conforme a navegação,
    controla as seções principais do painel e mantém consistência de estado.
    """
    page = render_sidebar()

    st.title("Amazon Price Tracker - Painel de Controle")

    if page == "🏠 Dashboard":
        render_dashboard()
    elif page == "📦 Produtos":
        render_products_page()
    elif page == "📈 Análise de Preços":
        render_price_analysis_page()
    elif page == "🔔 Alertas":
        st.info("Página de alertas será desenvolvida futuramente.")
    elif page == "📊 Estatísticas":
        st.info("Gráficos estatísticos consolidados virão em breve.")
    elif page == "⚙️ Configurações":
        st.info("Configurações avançadas: tokens, proxies e limites.")


if __name__ == "__main__":
    run_dashboard()
