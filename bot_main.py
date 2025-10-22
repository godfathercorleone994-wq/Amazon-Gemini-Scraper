"""
Main Telegram Bot Application
Amazon Product Scraper Bot for Telegram
"""
import asyncio
import sys
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)
from telegram.constants import ParseMode
from typing import Optional
import re

from config.settings import settings
from utils.logger import logger
from storage.mongodb_client import mongodb_client
from storage.redis_cache import redis_cache
from core.scraper_agent import ScraperAgent
from core.gemini_extractor import GeminiExtractor


class AmazonScraperBot:
    """Main Amazon Scraper Telegram Bot"""

    def __init__(self):
        """Initialize the bot"""
        if not settings.telegram_bot_token:
            logger.error("TELEGRAM_BOT_TOKEN not configured in environment")
            raise ValueError("TELEGRAM_BOT_TOKEN is required")
        
        self.token = settings.telegram_bot_token
        self.application = None
        self.extractor = GeminiExtractor()
        
        logger.info("Amazon Scraper Bot initialized")

    async def setup(self):
        """Setup bot and connect to databases"""
        try:
            # Connect to databases
            await mongodb_client.connect()
            await redis_cache.connect()
            logger.info("Database connections established")
            
            # Create application
            self.application = Application.builder().token(self.token).build()
            
            # Register command handlers
            self.application.add_handler(CommandHandler("start", self.cmd_start))
            self.application.add_handler(CommandHandler("help", self.cmd_help))
            self.application.add_handler(CommandHandler("scrape", self.cmd_scrape))
            self.application.add_handler(CommandHandler("track", self.cmd_track))
            self.application.add_handler(CommandHandler("list", self.cmd_list))
            self.application.add_handler(CommandHandler("stop", self.cmd_stop))
            self.application.add_handler(CommandHandler("alerts", self.cmd_alerts))
            self.application.add_handler(CommandHandler("stats", self.cmd_stats))
            
            # Handler for callbacks from inline buttons
            self.application.add_handler(CallbackQueryHandler(self.handle_callback))
            
            # Handler for direct messages (URLs)
            self.application.add_handler(
                MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message)
            )
            
            logger.info("Bot handlers registered successfully")
            
        except Exception as e:
            logger.error(f"Error during bot setup: {str(e)}")
            raise

    async def cmd_start(self, update: Update, context):
        """Handle /start command"""
        chat_id = update.effective_chat.id
        user = update.effective_user
        
        welcome_message = f"""
🚀 *Bem-vindo ao Amazon Price Tracker Bot!*

Olá {user.first_name}! 👋

Eu posso ajudar você a:
📊 Monitorar preços de produtos da Amazon
🔔 Receber alertas quando o preço cair
📈 Ver histórico de preços
🎯 Definir preços alvo

*Comandos disponíveis:*
/help - Mostra ajuda detalhada
/scrape - Extrai informações de um produto
/track - Rastreia um novo produto
/list - Lista seus produtos
/alerts - Gerencia alertas
/stats - Mostra estatísticas

*Como começar:*
1️⃣ Envie um link de produto da Amazon
2️⃣ Defina seu preço alvo
3️⃣ Receba notificações automáticas!

Seu Chat ID: `{chat_id}`
        """
        
        keyboard = [
            [
                InlineKeyboardButton("🔍 Extrair Produto", callback_data="action_scrape"),
                InlineKeyboardButton("📋 Meus Produtos", callback_data="action_list")
            ],
            [
                InlineKeyboardButton("❓ Ajuda", callback_data="action_help")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            welcome_message,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
        
        # Save user info
        try:
            db = mongodb_client.db
            await db.telegram_users.update_one(
                {"chat_id": chat_id},
                {
                    "$set": {
                        "chat_id": chat_id,
                        "username": user.username,
                        "first_name": user.first_name,
                        "last_name": user.last_name,
                        "is_active": True,
                    }
                },
                upsert=True
            )
            logger.info(f"User registered: {chat_id}")
        except Exception as e:
            logger.error(f"Error saving user: {str(e)}")

    async def cmd_help(self, update: Update, context):
        """Handle /help command"""
        help_text = """
📚 *AJUDA - Amazon Price Tracker Bot*

*Comandos Principais:*

🔍 */scrape [URL]* - Extrai dados de um produto
   Exemplo: `/scrape https://amazon.com/dp/B08N5WRWNW`

🎯 */track [URL] [preço]* - Rastreia um produto
   Exemplo: `/track https://amazon.com/dp/B08N5WRWNW 79.99`

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

1️⃣ *Extrair informações:*
   `/scrape https://amazon.com/dp/B08N5WRWNW`

2️⃣ *Rastrear com preço alvo:*
   `/track https://amazon.com/dp/B08N5WRWNW 79.99`

3️⃣ *Enviar apenas o link:*
   Envie: `https://amazon.com/dp/B08N5WRWNW`
   O bot perguntará o que fazer
        """
        
        await update.message.reply_text(
            help_text,
            parse_mode=ParseMode.MARKDOWN
        )

    async def cmd_scrape(self, update: Update, context):
        """Handle /scrape command - Extract product information"""
        chat_id = update.effective_chat.id
        
        if not context.args:
            await update.message.reply_text(
                "❌ *Uso incorreto!*\n\n"
                "Formato: `/scrape [URL]`\n"
                "Exemplo: `/scrape https://amazon.com/dp/B08N5WRWNW`",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        url = context.args[0]
        
        # Extract ASIN from URL
        asin = self.extract_asin(url)
        if not asin:
            await update.message.reply_text(
                "❌ URL inválida! Envie um link válido da Amazon.",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        processing_msg = await update.message.reply_text(
            "🔄 *Extraindo dados do produto...*\n"
            "Isso pode levar alguns segundos.",
            parse_mode=ParseMode.MARKDOWN
        )
        
        try:
            # Initialize scraper
            async with ScraperAgent() as scraper:
                # Scrape product
                result = await scraper.scrape_product(url)
                
                if result.status != "completed":
                    await processing_msg.edit_text(
                        "❌ *Erro ao acessar o produto*\n\n"
                        f"Status: {result.status}\n"
                        f"Erro: {result.error_message or 'Desconhecido'}",
                        parse_mode=ParseMode.MARKDOWN
                    )
                    return
                
                # Extract with AI
                product_data = await self.extractor.extract(result.html_content, url)
                
                if not product_data:
                    await processing_msg.edit_text(
                        "❌ *Erro ao extrair dados*\n\n"
                        "Não foi possível extrair informações do produto.",
                        parse_mode=ParseMode.MARKDOWN
                    )
                    return
            
            # Format response
            response_text = f"""
✅ *Produto Extraído com Sucesso!*

📦 *Título:* {product_data.get('title', 'N/A')}
💰 *Preço:* ${product_data.get('current_price', 'N/A')}
⭐ *Avaliação:* {product_data.get('rating', 'N/A')}/5
📊 *Reviews:* {product_data.get('review_count', 'N/A')}
🏷️ *ASIN:* `{asin}`

📝 *Descrição:*
{product_data.get('description', 'N/A')[:200]}...

🔗 [Ver na Amazon]({url})
            """
            
            keyboard = [
                [
                    InlineKeyboardButton(
                        "🎯 Rastrear Produto",
                        callback_data=f"track_{asin}"
                    )
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await processing_msg.delete()
            
            # Send with image if available
            if product_data.get('image_url'):
                await update.message.reply_photo(
                    photo=product_data['image_url'],
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
            
            # Cache product data
            await redis_cache.set(f"product:{asin}", product_data, ttl=3600)
            
        except Exception as e:
            logger.error(f"Error scraping product: {str(e)}")
            await processing_msg.edit_text(
                f"❌ *Erro ao processar produto*\n\n"
                f"Detalhes: {str(e)}\n\n"
                "Tente novamente mais tarde.",
                parse_mode=ParseMode.MARKDOWN
            )

    async def cmd_track(self, update: Update, context):
        """Handle /track command - Track product with price alert"""
        chat_id = update.effective_chat.id
        
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
        
        asin = self.extract_asin(url)
        if not asin:
            await update.message.reply_text(
                "❌ URL inválida! Envie um link válido da Amazon.",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        processing_msg = await update.message.reply_text(
            "🔄 *Processando produto...*",
            parse_mode=ParseMode.MARKDOWN
        )
        
        try:
            # Check if already tracked
            db = mongodb_client.db
            existing = await db.trackings.find_one(
                {"chat_id": chat_id, "asin": asin, "is_active": True}
            )
            
            if existing:
                await processing_msg.edit_text(
                    "⚠️ *Produto já está sendo rastreado!*\n\n"
                    f"Use /list para ver seus produtos.",
                    parse_mode=ParseMode.MARKDOWN
                )
                return
            
            # Get or scrape product data
            product_data = await redis_cache.get(f"product:{asin}")
            
            if not product_data:
                async with ScraperAgent() as scraper:
                    result = await scraper.scrape_product(url)
                    if result.status == "completed":
                        product_data = await self.extractor.extract(result.html_content, url)
                        await redis_cache.set(f"product:{asin}", product_data, ttl=3600)
                    else:
                        raise Exception(f"Failed to scrape: {result.error_message}")
            
            # Save tracking
            await db.trackings.insert_one({
                "chat_id": chat_id,
                "asin": asin,
                "url": url,
                "target_price": target_price,
                "current_price": product_data.get('current_price') if product_data else None,
                "title": product_data.get('title') if product_data else 'Unknown',
                "is_active": True,
            })
            
            response_text = f"""
✅ *Produto Adicionado para Rastreamento!*

📦 *{product_data.get('title', 'N/A') if product_data else 'Produto'}*
💰 Preço Atual: *${product_data.get('current_price', 'N/A') if product_data else 'N/A'}*
🎯 Preço Alvo: *${target_price or 'Não definido'}*

Você receberá notificações quando:
• O preço cair abaixo do seu alvo
• Houver uma grande promoção

Use /list para ver todos os seus produtos.
            """
            
            await processing_msg.delete()
            await update.message.reply_text(
                response_text,
                parse_mode=ParseMode.MARKDOWN
            )
            
        except Exception as e:
            logger.error(f"Error tracking product: {str(e)}")
            await processing_msg.edit_text(
                f"❌ *Erro ao rastrear produto*\n\nTente novamente.",
                parse_mode=ParseMode.MARKDOWN
            )

    async def cmd_list(self, update: Update, context):
        """Handle /list command - List tracked products"""
        chat_id = update.effective_chat.id
        
        try:
            db = mongodb_client.db
            trackings = await db.trackings.find(
                {"chat_id": chat_id, "is_active": True}
            ).to_list(20)
            
            if not trackings:
                await update.message.reply_text(
                    "📭 *Nenhum produto rastreado*\n\n"
                    "Use /track para começar a monitorar produtos!",
                    parse_mode=ParseMode.MARKDOWN
                )
                return
            
            message = "📋 *Seus Produtos Rastreados:*\n\n"
            
            for i, tracking in enumerate(trackings, 1):
                current = tracking.get('current_price', 'N/A')
                target = tracking.get('target_price', 'N/A')
                
                message += f"""
{i}. 📦 *{tracking.get('title', 'N/A')[:50]}*
   💰 Preço: ${current}
   🎯 Alvo: ${target}
   🏷️ ASIN: `{tracking['asin']}`
                """
            
            message += "\n\nUse /stop [ASIN] para parar o rastreamento."
            
            await update.message.reply_text(
                message,
                parse_mode=ParseMode.MARKDOWN
            )
            
        except Exception as e:
            logger.error(f"Error listing products: {str(e)}")
            await update.message.reply_text(
                "❌ Erro ao buscar produtos.",
                parse_mode=ParseMode.MARKDOWN
            )

    async def cmd_stop(self, update: Update, context):
        """Handle /stop command - Stop tracking a product"""
        chat_id = update.effective_chat.id
        
        if not context.args:
            await update.message.reply_text(
                "❌ *Uso incorreto!*\n\n"
                "Formato: `/stop [ASIN]`\n"
                "Exemplo: `/stop B08N5WRWNW`",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        asin = context.args[0].upper()
        
        try:
            db = mongodb_client.db
            result = await db.trackings.update_one(
                {"chat_id": chat_id, "asin": asin},
                {"$set": {"is_active": False}}
            )
            
            if result.modified_count > 0:
                await update.message.reply_text(
                    f"✅ *Rastreamento parado!*\n\n"
                    f"Produto {asin} removido da lista.",
                    parse_mode=ParseMode.MARKDOWN
                )
            else:
                await update.message.reply_text(
                    "⚠️ Produto não encontrado na sua lista.",
                    parse_mode=ParseMode.MARKDOWN
                )
                
        except Exception as e:
            logger.error(f"Error stopping tracking: {str(e)}")
            await update.message.reply_text(
                "❌ Erro ao parar rastreamento.",
                parse_mode=ParseMode.MARKDOWN
            )

    async def cmd_alerts(self, update: Update, context):
        """Handle /alerts command - Manage alerts"""
        chat_id = update.effective_chat.id
        
        try:
            db = mongodb_client.db
            alert_count = await db.trackings.count_documents(
                {"chat_id": chat_id, "is_active": True, "target_price": {"$exists": True}}
            )
            
            message = f"""
🔔 *Gerenciamento de Alertas*

📊 Alertas Ativos: *{alert_count}*

*Configurações:*
• Notificações: ✅ Ativadas
• Tipo: Instantâneo
• Horário: 24h

Para definir um alerta de preço:
`/track [URL] [preço_alvo]`

Exemplo:
`/track https://amazon.com/dp/B08N5WRWNW 79.99`
            """
            
            await update.message.reply_text(
                message,
                parse_mode=ParseMode.MARKDOWN
            )
            
        except Exception as e:
            logger.error(f"Error showing alerts: {str(e)}")
            await update.message.reply_text(
                "❌ Erro ao buscar alertas.",
                parse_mode=ParseMode.MARKDOWN
            )

    async def cmd_stats(self, update: Update, context):
        """Handle /stats command - Show statistics"""
        chat_id = update.effective_chat.id
        
        try:
            db = mongodb_client.db
            
            total_tracked = await db.trackings.count_documents(
                {"chat_id": chat_id, "is_active": True}
            )
            
            total_alerts = await db.trackings.count_documents(
                {"chat_id": chat_id, "is_active": True, "target_price": {"$exists": True}}
            )
            
            message = f"""
📊 *Suas Estatísticas*

📦 Produtos Rastreados: *{total_tracked}*
🔔 Alertas Configurados: *{total_alerts}*

Use /list para ver seus produtos.
            """
            
            await update.message.reply_text(
                message,
                parse_mode=ParseMode.MARKDOWN
            )
            
        except Exception as e:
            logger.error(f"Error showing stats: {str(e)}")
            await update.message.reply_text(
                "❌ Erro ao buscar estatísticas.",
                parse_mode=ParseMode.MARKDOWN
            )

    async def handle_callback(self, update: Update, context):
        """Handle inline button callbacks"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        if data.startswith("action_"):
            action = data.replace("action_", "")
            
            if action == "scrape":
                await query.message.reply_text(
                    "📝 *Como extrair dados de um produto:*\n\n"
                    "Envie o link do produto da Amazon ou use:\n"
                    "`/scrape [URL]`",
                    parse_mode=ParseMode.MARKDOWN
                )
            elif action == "list":
                # Simulate list command
                update.effective_chat = query.message.chat
                await self.cmd_list(update, context)
            elif action == "help":
                await self.cmd_help(update, context)
        
        elif data.startswith("track_"):
            asin = data.replace("track_", "")
            await query.message.reply_text(
                f"🎯 *Rastrear Produto*\n\n"
                f"Para rastrear este produto, use:\n"
                f"`/track https://amazon.com/dp/{asin} [preço_alvo]`\n\n"
                f"Exemplo:\n"
                f"`/track https://amazon.com/dp/{asin} 79.99`",
                parse_mode=ParseMode.MARKDOWN
            )

    async def handle_message(self, update: Update, context):
        """Handle text messages (URLs)"""
        text = update.message.text
        
        # Check if it's an Amazon URL
        if "amazon.com" in text.lower() or "amzn.to" in text.lower():
            url_pattern = r'https?://[^\s]+'
            urls = re.findall(url_pattern, text)
            
            if urls:
                # Ask what to do
                keyboard = [
                    [
                        InlineKeyboardButton("🔍 Extrair Dados", callback_data="action_scrape"),
                        InlineKeyboardButton("🎯 Rastrear", callback_data=f"track_{self.extract_asin(urls[0]) or 'unknown'}")
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(
                    "🔗 *Link da Amazon detectado!*\n\n"
                    "O que você gostaria de fazer?",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=reply_markup
                )
                
                # Store URL in context
                context.user_data['last_url'] = urls[0]
        else:
            await update.message.reply_text(
                "🤔 Não entendi seu comando.\n\n"
                "Envie um link da Amazon ou use /help para ver os comandos disponíveis.",
                parse_mode=ParseMode.MARKDOWN
            )

    def extract_asin(self, url: str) -> Optional[str]:
        """Extract ASIN from Amazon URL"""
        patterns = [
            r'/dp/([A-Z0-9]{10})',
            r'/gp/product/([A-Z0-9]{10})',
            r'/ASIN/([A-Z0-9]{10})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        return None

    async def start(self):
        """Start the bot"""
        try:
            logger.info("Starting Amazon Scraper Telegram Bot...")
            
            # Setup
            await self.setup()
            
            # Run polling
            logger.info("Bot is running! Press Ctrl+C to stop.")
            await self.application.run_polling(drop_pending_updates=True)
            
        except Exception as e:
            logger.error(f"Error starting bot: {str(e)}")
            raise

    async def shutdown(self):
        """Shutdown the bot gracefully"""
        logger.info("Shutting down bot...")
        
        try:
            if self.application:
                await self.application.stop()
            
            await mongodb_client.disconnect()
            await redis_cache.disconnect()
            
            logger.info("Bot shutdown complete")
        except Exception as e:
            logger.error(f"Error during shutdown: {str(e)}")


async def main():
    """Main entry point"""
    bot = AmazonScraperBot()
    
    try:
        await bot.start()
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        sys.exit(1)
    finally:
        await bot.shutdown()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
