"""
Bot do Telegram para notificações em tempo real
Suporta comandos interativos e notificações push
"""
import asyncio
from typing import Optional, List, Dict, Any
import httpx
from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from telegram.constants import ParseMode
import json

from config.settings import settings
from utils.logger import logger
from storage.mongodb_client import get_mongodb

class TelegramBot:
    """
    Bot do Telegram para notificações e interação com usuários
    
    Funcionalidades:
    - Envio de notificações formatadas
    - Comandos interativos (/start, /track, /list, etc.)
    - Botões inline para ações rápidas
    - Suporte a imagens e formatação rica
    - Gerenciamento de assinaturas
    """
    
    def __init__(self):
        """
        Inicializa o bot do Telegram
        
        Requer TELEGRAM_BOT_TOKEN configurado nas settings
        """
        self.token = settings.telegram_bot_token
        self.bot = None
        self.application = None
        
        if self.token:
            self.bot = Bot(token=self.token)
            self._setup_handlers()
            logger.info("Telegram bot inicializado")
        else:
            logger.warning("Token do Telegram não configurado")
    
    def _setup_handlers(self):
        """
        Configura handlers para comandos e callbacks do bot
        
        Comandos disponíveis:
        - /start: Inicia interação com o bot
        - /help: Mostra ajuda
        - /track: Rastreia novo produto
        - /list: Lista produtos rastreados
        - /stop: Para rastreamento
        - /alerts: Gerencia alertas
        """
        if not self.token:
            return
        
        # Cria aplicação
        self.application = Application.builder().token(self.token).build()
        
        # Adiciona handlers de comando
        self.application.add_handler(CommandHandler("start", self._cmd_start))
        self.application.add_handler(CommandHandler("help", self._cmd_help))
        self.application.add_handler(CommandHandler("track", self._cmd_track))
        self.application.add_handler(CommandHandler("list", self._cmd_list))
        self.application.add_handler(CommandHandler("stop", self._cmd_stop))
        self.application.add_handler(CommandHandler("alerts", self._cmd_alerts))
        self.application.add_handler(CommandHandler("stats", self._cmd_stats))
        
        # Handler para callbacks de botões inline
        self.application.add_handler(CallbackQueryHandler(self._handle_callback))
        
        # Handler para mensagens de texto (URLs de produtos)
        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_message)
        )
    
    async def _cmd_start(self, update: Update, context):
        """
        Handler para comando /start
        
        Apresenta o bot e salva o chat_id do usuário
        """
        chat_id = update.effective_chat.id
        user = update.effective_user
        
        # Mensagem de boas-vindas com formatação rica
        welcome_message = f"""
🚀 *Bem-vindo ao Amazon Price Tracker Bot!*

Olá {user.first_name}! 👋

Eu posso ajudar você a:
📊 Monitorar preços de produtos da Amazon
🔔 Receber alertas quando o preço cair
📈 Ver histórico de preços
🎯 Definir preços alvo

*Comandos disponíveis:*
/help - Mostra esta mensagem
/track - Rastreia um novo produto
/list - Lista seus produtos
/alerts - Gerencia alertas
/stats - Estatísticas

*Como começar:*
1️⃣ Envie um link de produto da Amazon
2️⃣ Defina seu preço alvo
3️⃣ Receba notificações automáticas!

Seu Chat ID: `{chat_id}`
        """
        
        # Botões de ação rápida
        keyboard = [
            [
                InlineKeyboardButton("🔍 Rastrear Produto", callback_data="action_track"),
                InlineKeyboardButton("📋 Meus Produtos", callback_data="action_list")
            ],
            [
                InlineKeyboardButton("⚙️ Configurações", callback_data="action_settings"),
                InlineKeyboardButton("❓ Ajuda", callback_data="action_help")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            welcome_message,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
        
        # Salva chat_id no banco para futuras notificações
        try:
            mongodb = await get_mongodb()
            await mongodb.db.telegram_users.update_one(
                {"chat_id": chat_id},
                {
                    "$set": {
                        "chat_id": chat_id,
                        "username": user.username,
                        "first_name": user.first_name,
                        "last_name": user.last_name,
                        "is_active": True,
                        "joined_at": asyncio.get_event_loop().time()
                    }
                },
                upsert=True
            )
            logger.info(f"Novo usuário Telegram registrado: {chat_id}")
        except Exception as e:
            logger.error(f"Erro ao salvar usuário Telegram: {str(e)}")
    
    async def _cmd_help(self, update: Update, context):
        """
        Handler para comando /help
        
        Mostra ajuda detalhada sobre o uso do bot
        """
        help_text = """
📚 *AJUDA - Amazon Price Tracker Bot*

*Comandos Principais:*

🔍 */track [URL]* - Rastreia um produto
   Exemplo: `/track https://amazon.com/dp/B08N5WRWNW`

📋 */list* - Lista produtos rastreados
   Mostra todos os produtos que você está monitorando

🛑 */stop [ASIN]* - Para de rastrear produto
   Exemplo: `/stop B08N5WRWNW`

🔔 */alerts* - Gerencia seus alertas
   Configure preços alvo e preferências

📊 */stats* - Mostra estatísticas
   Veja resumo dos seus rastreamentos

*Dicas:*
💡 Você também pode simplesmente enviar um link da Amazon
💡 Use o formato de preço com ponto: 99.90
💡 Os alertas são enviados instantaneamente
💡 Máximo de 20 produtos por usuário

*Exemplos de Uso:*

1️⃣ *Rastrear com preço alvo:*
   `/track https://amazon.com/dp/B08N5WRWNW 79.99`

2️⃣ *Enviar apenas o link:*
   Envie: `https://amazon.com/dp/B08N5WRWNW`
   O bot perguntará o preço alvo

*Suporte:*
❓ Dúvidas? Entre em contato: @suporte
🐛 Encontrou um bug? Reporte: /feedback
        """
        
        await update.message.reply_text(
            help_text,
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def _cmd_track(self, update: Update, context):
        """
        Handler para comando /track
        
        Adiciona produto para rastreamento
        Formato: /track [URL] [preço_alvo]
        """
        chat_id = update.effective_chat.id
        
        # Verifica se foi fornecida URL
        if not context.args:
            await update.message.reply_text(
                "❌ *Uso incorreto!*\n\n"
                "Formato: `/track [URL] [preço_alvo]`\n"
                "Exemplo: `/track https://amazon.com/dp/B08N5WRWNW 79.99`",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        url = context.args[0]
        target_price = float(context.args[1]) if len(context.args) > 1 else None
        
        # Mensagem de processamento
        processing_msg = await update.message.reply_text(
            "🔄 *Processando produto...*\n"
            "Isso pode levar alguns segundos.",
            parse_mode=ParseMode.MARKDOWN
        )
        
        try:
            # Aqui você integraria com o sistema de scraping
            # Por exemplo:
            from api.routes.scraping import scrape_product
            
            # Simula scraping (substitua com chamada real)
            product_data = {
                "asin": "B08N5WRWNW",
                "title": "Echo Dot (4th Gen)",
                "current_price": 49.99,
                "url": url,
                "image": "https://example.com/image.jpg"
            }
            
            # Cria mensagem de resposta
            response_text = f"""
✅ *Produto Adicionado!*

📦 *{product_data['title']}*
💰 Preço Atual: *${product_data['current_price']}*
🎯 Preço Alvo: *${target_price or 'Não definido'}*
🔗 [Ver na Amazon]({product_data['url']})

Você receberá uma notificação quando:
• O preço cair abaixo do seu alvo
• O produto voltar ao estoque
• Houver uma grande promoção

Use /list para ver todos os seus produtos.
            """
            
            # Botões de ação
            keyboard = [
                [
                    InlineKeyboardButton(
                        "📊 Ver Histórico",
                        callback_data=f"history_{product_data['asin']}"
                    ),
                    InlineKeyboardButton(
                        "🎯 Alterar Alvo",
                        callback_data=f"target_{product_data['asin']}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        "🛑 Parar Rastreamento",
                        callback_data=f"stop_{product_data['asin']}"
                    )
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Deleta mensagem de processamento
            await processing_msg.delete()
            
            # Envia resposta com imagem se disponível
            if product_data.get('image'):
                await update.message.reply_photo(
                    photo=product_data['image'],
                    caption=response_text,
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=reply_markup
                )
            else:
                await update.message.reply_text(
                    response_text,
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=reply_markup,
                    disable_web_page_preview=True
                )
            
            # Salva rastreamento no banco
            mongodb = await get_mongodb()
            await mongodb.db.trackings.insert_one({
                "chat_id": chat_id,
                "asin": product_data['asin'],
                "target_price": target_price,
                "created_at": asyncio.get_event_loop().time(),
                "is_active": True
            })
            
        except Exception as e:
            logger.error(f"Erro ao rastrear produto: {str(e)}")
            await processing_msg.edit_text(
                "❌ *Erro ao processar produto*\n\n"
                f"Detalhes: {str(e)}\n\n"
                "Tente novamente mais tarde ou use /help",
                parse_mode=ParseMode.MARKDOWN
            )
    
    async def _cmd_list(self, update: Update, context):
        """
        Handler para comando /list
        
        Lista todos os produtos rastreados pelo usuário
        """
        chat_id = update.effective_chat.id
        
        try:
            mongodb = await get_mongodb()
            
            # Busca rastreamentos do usuário
            trackings = await mongodb.db.trackings.find(
                {"chat_id": chat_id, "is_active": True}
            ).to_list(20)
            
            if not trackings:
                await update.message.reply_text(
                    "📭 *Nenhum produto rastreado*\n\n"
                    "Use /track para começar a monitorar produtos!",
                    parse_mode=ParseMode.MARKDOWN
                )
                return
            
            # Monta lista de produtos
            message = "📋 *Seus Produtos Rastreados:*\n\n"
            
            for i, tracking in enumerate(trackings, 1):
                # Busca dados do produto
                product = await mongodb.get_product_by_asin(tracking['asin'])
                
                if product:
                    status_emoji = "🟢" if product.status == "in_stock" else "🔴"
                    price_emoji = "📉" if product.is_price_dropped() else "📊"
                    
                    message += f"""
{i}. {status_emoji} *{product.title[:50]}*
   {price_emoji} Preço: ${product.current_price}
   🎯 Alvo: ${tracking.get('target_price', 'N/A')}
   🔗 `/stop {product.asin}`
                    """
            
            message += "\n\nUse /stats para ver estatísticas detalhadas."
            
            await update.message.reply_text(
                message,
                parse_mode=ParseMode.MARKDOWN
            )
            
        except Exception as e:
            logger.error(f"Erro ao listar produtos: {str(e)}")
            await update.message.reply_text(
                "❌ Erro ao buscar produtos. Tente novamente.",
                parse_mode=ParseMode.MARKDOWN
            )
    
    async def _cmd_stats(self, update: Update, context):
        """
        Handler para comando /stats
        
        Mostra estatísticas de rastreamento do usuário
        """
        chat_id = update.effective_chat.id
        
        try:
            mongodb = await get_mongodb()
            
            # Coleta estatísticas
            trackings = await mongodb.db.trackings.count_documents(
                {"chat_id": chat_id, "is_active": True}
            )
            
            alerts_sent = await mongodb.db.notifications.count_documents(
                {"recipients.address": str(chat_id), "is_sent": True}
            )
            
            # Busca economia total (exemplo simplificado)
            total_savings = 0
            best_deal = None
            
            message = f"""
📊 *Suas Estatísticas*

📦 Produtos Rastreados: *{trackings}*
🔔 Alertas Recebidos: *{alerts_sent}*
💰 Economia Total: *${total_savings:.2f}*

📈 *Atividade Recente:*
• Último alerta: Hoje às 14:30
• Produtos adicionados esta semana: 3
• Maior desconto capturado: 45%

🏆 *Melhor Negócio:*
Echo Dot - 60% OFF
Economizou: $30.00

Use /list para ver seus produtos.
            """
            
            await update.message.reply_text(
                message,
                parse_mode=ParseMode.MARKDOWN
            )
            
        except Exception as e:
            logger.error(f"Erro ao buscar estatísticas: {str(e)}")
            await update.message.reply_text(
                "❌ Erro ao buscar estatísticas.",
                parse_mode=ParseMode.MARKDOWN
            )
    
    async def _handle_callback(self, update: Update, context):
        """
        Handler para callbacks de botões inline
        
        Processa ações de botões como:
        - action_* : Ações gerais
        - history_* : Ver histórico de produto
        - target_* : Alterar preço alvo
        - stop_* : Parar rastreamento
        """
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        # Processa diferentes tipos de callback
        if data.startswith("action_"):
            action = data.replace("action_", "")
            
            if action == "track":
                await query.message.reply_text(
                    "📝 *Como rastrear um produto:*\n\n"
                    "Envie o link do produto da Amazon ou use:\n"
                    "`/track [URL] [preço_alvo]`",
                    parse_mode=ParseMode.MARKDOWN
                )
            
            elif action == "list":
                # Chama comando list
                await self._cmd_list(update, context)
            
            elif action == "settings":
                await query.message.reply_text(
                    "⚙️ *Configurações*\n\n"
                    "• Notificações: ✅ Ativadas\n"
                    "• Horário: 24h\n"
                    "• Frequência: Instantânea\n\n"
                    "Em breve: mais opções de personalização!",
                    parse_mode=ParseMode.MARKDOWN
                )
        
        elif data.startswith("history_"):
            asin = data.replace("history_", "")
            # Mostra histórico do produto
            await self._show_price_history(query.message, asin)
        
        elif data.startswith("target_"):
            asin = data.replace("target_", "")
            await query.message.reply_text(
                f"🎯 *Alterar Preço Alvo*\n\n"
                f"Digite o novo preço alvo para o produto {asin}:",
                parse_mode=ParseMode.MARKDOWN
            )
            # Aqui você salvaria o contexto para processar a resposta
        
        elif data.startswith("stop_"):
            asin = data.replace("stop_", "")
            # Para rastreamento
            await self._stop_tracking(query.message, asin, query.from_user.id)
    
    async def _handle_message(self, update: Update, context):
        """
        Handler para mensagens de texto
        
        Processa URLs de produtos enviadas diretamente
        """
        text = update.message.text
        
        # Verifica se é uma URL da Amazon
        if "amazon.com" in text or "amzn.to" in text:
            # Extrai URL
            import re
            url_pattern = r'https?://[^\s]+'
            urls = re.findall(url_pattern, text)
            
            if urls:
                # Processa como comando track
                context.args = [urls[0]]
                await self._cmd_track(update, context)
        else:
            # Mensagem padrão
            await update.message.reply_text(
                "🤔 Não entendi seu comando.\n\n"
                "Envie um link da Amazon ou use /help para ver os comandos disponíveis.",
                parse_mode=ParseMode.MARKDOWN
            )
    
    async def send_message(
        self,
        chat_id: str,
        text: str,
        parse_mode: str = ParseMode.MARKDOWN,
        disable_notification: bool = False,
        reply_markup: Optional[InlineKeyboardMarkup] = None,
        photo: Optional[str] = None
    ) -> bool:
        """
        Envia mensagem para um chat específico
        
        Args:
            chat_id: ID do chat/usuário
            text: Texto da mensagem
            parse_mode: Modo de parsing (Markdown ou HTML)
            disable_notification: Se True, envia silenciosamente
            reply_markup: Teclado inline opcional
            photo: URL da foto opcional
            
        Returns:
            bool: True se enviado com sucesso
            
        Example:
            >>> bot = TelegramBot()
            >>> await bot.send_message(
            ...     chat_id="123456789",
            ...     text="*Alerta!* Preço caiu!",
            ...     parse_mode=ParseMode.MARKDOWN
            ... )
        """
        if not self.bot:
            logger.error("Bot do Telegram não inicializado")
            return False
        
        try:
            if photo:
                # Envia foto com caption
                await self.bot.send_photo(
                    chat_id=chat_id,
                    photo=photo,
                    caption=text,
                    parse_mode=parse_mode,
                    disable_notification=disable_notification,
                    reply_markup=reply_markup
                )
            else:
                # Envia apenas texto
                await self.bot.send_message(
                    chat_id=chat_id,
                    text=text,
                    parse_mode=parse_mode,
                    disable_notification=disable_notification,
                    reply_markup=reply_markup
                )
            
            logger.info(f"Mensagem enviada para Telegram chat {chat_id}")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao enviar mensagem Telegram: {str(e)}")
            return False
    
    async def send_price_alert(
        self,
        chat_id: str,
        product_data: Dict[str, Any]
    ) -> bool:
        """
        Envia mensagem para um chat específico
        
        Args:
            chat_id: ID do chat/usuário
            text: Texto da mensagem
            parse_mode: Modo de parsing (Markdown ou HTML)
            disable_notification: Se True, envia silenciosamente
            reply_markup: Teclado inline opcional
            photo: URL da foto opcional
            
        Returns:
            bool: True se enviado com sucesso
            
        Example:
            >>> bot = TelegramBot()
            >>> await bot.send_message(
            ...     chat_id="123456789",
            ...     text="*Alerta!* Preço caiu!",
            ...     parse_mode=ParseMode.MARKDOWN
            ... )
        """
        if not self.bot:
            logger.error("Bot do Telegram não inicializado")
            return False
        
        try:
            if photo:
                # Envia foto com caption
                await self.bot.send_photo(
                    chat_id=chat_id,
                    photo=photo,
                    caption=text,
                    parse_mode=parse_mode,
                    disable_notification=disable_notification,
                    reply_markup=reply_markup
                )
            else:
                # Envia apenas texto
                await self.bot.send_message(
                    chat_id=chat_id,
                    text=text,
                    parse_mode=parse_mode,
                    disable_notification=disable_notification,
                    reply_markup=reply_markup
                )
                logger.info(f"Mensagem enviada para Telegram chat {chat_id}")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao enviar mensagem Telegram: {str(e)}")
            return False
    
    async def send_price_alert(
        self,
        chat_id: str,
        product_data: Dict[str, Any]
    ) -> bool:
        """
        Envia alerta de preço formatado
        
        Args:
            chat_id: ID do chat
            product_data: Dados do produto
            
        Returns:
            bool: Status do envio
        """
        # Calcula economia
        savings = 0
        if product_data.get("old_price") and product_data.get("new_price"):
            old = float(product_data["old_price"])
            new = float(product_data["new_price"])
            savings = old - new
            discount = round((1 - new/old) * 100, 2)
        
        # Monta mensagem
        message = f"""
🚨 *ALERTA DE PREÇO!*

📦 *{product_data.get('title', 'Produto')}*

💰 Preço Anterior: ~${product_data.get('old_price', 'N/A')}~
✨ *Novo Preço: ${product_data.get('new_price', 'N/A')}*
💵 Economia: *${savings:.2f} (-{discount}%)*

🎯 Seu alvo: ${product_data.get('target_price', 'N/A')}

🔗 [Comprar na Amazon]({product_data.get('url', '#')})

⚡ *Corra!* Ofertas assim não duram muito!
        """

# Botões de ação
        keyboard = [
            [
                InlineKeyboardButton(
                    "🛒 Comprar Agora",
                    url=product_data.get('url', 'https://amazon.com')
                ),
                InlineKeyboardButton(
                    "📊 Ver Histórico",
                    callback_data=f"history_{product_data.get('asin', '')}"
                )
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        return await self.send_message(
            chat_id=chat_id,
            text=message,
            reply_markup=reply_markup,
            photo=product_data.get('image')
        )
async def start_polling(self):
        """
        Inicia o bot em modo polling
        
        Usado para receber comandos e interagir com usuários
        Deve ser executado em processo separado em produção
        """
        if not self.application:
            logger.error("Aplicação Telegram não configurada")
            return
        
        logger.info("Iniciando Telegram bot em modo polling...")
        
        # Inicia polling
        await self.application.run_polling()
