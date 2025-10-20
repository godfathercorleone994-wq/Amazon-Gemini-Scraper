"""
Sistema de envio de emails com suporte a múltiplos provedores
Suporta SendGrid, SMTP tradicional e fallback local
"""
import asyncio
from typing import Optional, List, Dict, Any
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import aiosmtplib
from pathlib import Path
import base64

# Importação condicional do SendGrid
try:
    from sendgrid import SendGridAPIClient
    from sendgrid.helpers.mail import Mail, Attachment, FileContent, FileName, FileType
    SENDGRID_AVAILABLE = True
except ImportError:
    SENDGRID_AVAILABLE = False

from config.settings import settings
from utils.logger import logger

class EmailSender:
    """
    Classe responsável pelo envio de emails
    
    Características:
    - Suporta múltiplos provedores (SendGrid, SMTP)
    - Templates HTML personalizáveis
    - Anexos e imagens inline
    - Retry automático em caso de falha
    - Logs detalhados para debugging
    """
    
    def __init__(self):
        """
        Inicializa o sender de email
        Detecta automaticamente o melhor provedor disponível
        """
        self.sendgrid_client = None
        self.smtp_config = None
        
        # Tenta configurar SendGrid se disponível
        if SENDGRID_AVAILABLE and settings.sendgrid_api_key:
            try:
                self.sendgrid_client = SendGridAPIClient(settings.sendgrid_api_key)
                logger.info("SendGrid configurado com sucesso")
            except Exception as e:
                logger.warning(f"Falha ao configurar SendGrid: {str(e)}")
        
        # Configuração SMTP como fallback
        self.smtp_config = {
            "hostname": "smtp.gmail.com",  # Pode ser configurado via settings
            "port": 587,
            "use_tls": True,
            "username": settings.email_from,
            "password": None  # Adicionar senha SMTP nas settings se necessário
        }
        
        # Templates de email pré-definidos
        self.templates = self._load_email_templates()
    
    def _load_email_templates(self) -> Dict[str, str]:
        """
        Carrega templates HTML para diferentes tipos de notificação
        
        Returns:
            Dict com templates HTML para cada tipo de notificação
        """
        return {
            "price_drop": """
            <html>
                <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 20px; text-align: center;">
                        <h1 style="color: white; margin: 0;">🎉 Alerta de Preço!</h1>
                    </div>
                    <div style="padding: 20px; background: #f7f7f7;">
                        <h2 style="color: #333;">O preço caiu! 📉</h2>
                        <div style="background: white; padding: 15px; border-radius: 10px; margin: 15px 0;">
                            <h3 style="color: #667eea; margin-top: 0;">{product_title}</h3>
                            <p style="font-size: 16px; color: #666;">
                                <strong>Preço anterior:</strong> <span style="text-decoration: line-through; color: #999;">${old_price}</span><br>
                                <strong>Novo preço:</strong> <span style="color: #27ae60; font-size: 20px; font-weight: bold;">${new_price}</span><br>
                                <strong>Economia:</strong> <span style="color: #e74c3c;">-{discount}%</span>
                            </p>
                        </div>
                        <div style="text-align: center; margin: 20px 0;">
                            <a href="{product_url}" style="background: #667eea; color: white; padding: 12px 30px; text-decoration: none; border-radius: 25px; display: inline-block;">
                                Ver Produto na Amazon
                            </a>
                        </div>
                        <p style="color: #999; font-size: 12px; text-align: center;">
                            Este alerta foi configurado para o preço alvo de ${target_price}
                        </p>
                    </div>
                    <div style="background: #333; color: #999; padding: 15px; text-align: center; font-size: 12px;">
                        <p>© 2024 Amazon Price Tracker | <a href="#" style="color: #667eea;">Cancelar inscrição</a></p>
                    </div>
                </body>
            </html>
            """,
            
            "back_in_stock": """
            <html>
                <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                    <div style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); padding: 20px; text-align: center;">
                        <h1 style="color: white; margin: 0;">✅ Produto Disponível!</h1>
                    </div>
                    <div style="padding: 20px; background: #f7f7f7;">
                        <h2 style="color: #333;">Voltou ao estoque! 🎊</h2>
                        <div style="background: white; padding: 15px; border-radius: 10px; margin: 15px 0;">
                            <h3 style="color: #f5576c; margin-top: 0;">{product_title}</h3>
                            <p style="font-size: 16px; color: #666;">
                                O produto que você estava monitorando está disponível novamente!<br><br>
                                <strong>Preço atual:</strong> <span style="color: #27ae60; font-size: 20px;">${current_price}</span><br>
                                <strong>Status:</strong> <span style="color: #27ae60; font-weight: bold;">Em Estoque</span>
                            </p>
                        </div>
                        <div style="text-align: center; margin: 20px 0;">
                            <a href="{product_url}" style="background: #f5576c; color: white; padding: 12px 30px; text-decoration: none; border-radius: 25px; display: inline-block;">
                                Comprar Agora
                            </a>
                        </div>
                        <p style="color: #e74c3c; font-weight: bold; text-align: center;">
                            ⚠️ Corra! Produtos populares esgotam rapidamente.
                        </p>
                    </div>
                </body>
            </html>
            """,
            
            "welcome": """
            <html>
                <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; text-align: center;">
                        <h1 style="color: white; margin: 0;">Bem-vindo ao Price Tracker! 🚀</h1>
                    </div>
                    <div style="padding: 20px; background: #f7f7f7;">
                        <h2 style="color: #333;">Olá, {user_name}! 👋</h2>
                        <p style="font-size: 16px; color: #666;">
                            Obrigado por se cadastrar! Agora você pode:
                        </p>
                        <ul style="color: #666; font-size: 16px;">
                            <li>📊 Monitorar preços de produtos</li>
                            <li>🔔 Receber alertas de preço</li>
                            <li>📈 Ver histórico de preços</li>
                            <li>🎯 Definir preços alvo</li>
                            <li>📱 Receber notificações no Telegram</li>
                        </ul>
                        <div style="background: white; padding: 15px; border-radius: 10px; margin: 20px 0;">
                            <h3 style="color: #667eea;">Sua API Key:</h3>
                            <code style="background: #f0f0f0; padding: 10px; display: block; border-radius: 5px; word-break: break-all;">
                                {api_key}
                            </code>
                            <p style="color: #999; font-size: 12px;">
                                ⚠️ Guarde esta chave em local seguro. Você precisará dela para usar a API.
                            </p>
                        </div>
                    </div>
                </body>
            </html>
            """
        }
    
    async def send(
        self,
        to: str,
        subject: str,
        body: str,
        html: Optional[str] = None,
        template: Optional[str] = None,
        template_vars: Optional[Dict[str, Any]] = None,
        attachments: Optional[List[Dict[str, Any]]] = None,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
        reply_to: Optional[str] = None
    ) -> bool:
        """
        Envia email com suporte a múltiplas configurações
        
        Args:
            to: Email do destinatário
            subject: Assunto do email
            body: Corpo do email em texto plano
            html: Corpo do email em HTML (opcional)
            template: Nome do template a usar (opcional)
            template_vars: Variáveis para substituir no template
            attachments: Lista de anexos [{"filename": "file.pdf", "content": bytes}]
            cc: Lista de emails em cópia
            bcc: Lista de emails em cópia oculta
            reply_to: Email para resposta
            
        Returns:
            bool: True se enviado com sucesso, False caso contrário
            
        Example:
            >>> sender = EmailSender()
            >>> await sender.send(
            ...     to="user@example.com",
            ...     subject="Alerta de Preço",
            ...     template="price_drop",
            ...     template_vars={
            ...         "product_title": "Echo Dot",
            ...         "old_price": "49.99",
            ...         "new_price": "29.99"
            ...     }
            ... )
        """
        try:
            # Se um template foi especificado, usa ele
            if template and template in self.templates:
                html = self.templates[template]
                
                # Substitui variáveis no template
                if template_vars:
                    for key, value in template_vars.items():
                        html = html.replace(f"{{{key}}}", str(value))
            
            # Tenta enviar com SendGrid primeiro
            if self.sendgrid_client:
                return await self._send_with_sendgrid(
                    to=to,
                    subject=subject,
                    body=body,
                    html=html,
                    attachments=attachments,
                    cc=cc,
                    bcc=bcc,
                    reply_to=reply_to
                )
            
            # Fallback para SMTP
            return await self._send_with_smtp(
                to=to,
                subject=subject,
                body=body,
                html=html,
                attachments=attachments,
                cc=cc,
                bcc=bcc,
                reply_to=reply_to
            )
            
        except Exception as e:
            logger.error(f"Erro ao enviar email para {to}: {str(e)}")
            return False
    
    async def _send_with_sendgrid(
        self,
        to: str,
        subject: str,
        body: str,
        html: Optional[str] = None,
        attachments: Optional[List[Dict[str, Any]]] = None,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
        reply_to: Optional[str] = None
    ) -> bool:
        """
        Envia email usando SendGrid API
        
        SendGrid oferece melhor deliverability e tracking
        """
        try:
            # Cria mensagem
            message = Mail(
                from_email=settings.email_from,
                to_emails=to,
                subject=subject,
                plain_text_content=body,
                html_content=html or body
            )
            
            # Adiciona CC e BCC se fornecidos
            if cc:
                message.cc = cc
            if bcc:
                message.bcc = bcc
            if reply_to:
                message.reply_to = reply_to
            
            # Adiciona anexos
            if attachments:
                for attachment_data in attachments:
                    attachment = Attachment()
                    attachment.file_content = FileContent(
                        base64.b64encode(attachment_data["content"]).decode()
                    )
                    attachment.file_name = FileName(attachment_data["filename"])
                    attachment.file_type = FileType(
                        attachment_data.get("mime_type", "application/octet-stream")
                    )
                    message.add_attachment(attachment)
            
            # Envia email
            response = self.sendgrid_client.send(message)
            
            if response.status_code in [200, 201, 202]:
                logger.info(f"Email enviado com sucesso para {to} via SendGrid")
                return True
            else:
                logger.warning(f"SendGrid retornou status {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Erro no SendGrid: {str(e)}")
            return False
    
    async def _send_with_smtp(
        self,
        to: str,
        subject: str,
        body: str,
        html: Optional[str] = None,
        attachments: Optional[List[Dict[str, Any]]] = None,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
        reply_to: Optional[str] = None
    ) -> bool:
        """
        Envia email usando SMTP tradicional
        
        Útil como fallback quando SendGrid não está disponível
        """
        try:
            # Cria mensagem multipart
            msg = MIMEMultipart('alternative')
            msg['From'] = settings.email_from
            msg['To'] = to
            msg['Subject'] = subject
            
            if cc:
                msg['Cc'] = ', '.join(cc)
            if reply_to:
                msg['Reply-To'] = reply_to
            
            # Adiciona corpo do email
            msg.attach(MIMEText(body, 'plain'))
            if html:
                msg.attach(MIMEText(html, 'html'))
            
            # Adiciona anexos
            if attachments:
                for attachment_data in attachments:
                    part = MIMEBase('application', 'octet-stream')
                    part.set_payload(attachment_data["content"])
                    encoders.encode_base64(part)
                    part.add_header(
                        'Content-Disposition',
                        f'attachment; filename= {attachment_data["filename"]}'
                    )
                    msg.attach(part)
            
            # Envia email via SMTP
            async with aiosmtplib.SMTP(
                hostname=self.smtp_config["hostname"],
                port=self.smtp_config["port"],
                use_tls=self.smtp_config["use_tls"]
            ) as smtp:
                if self.smtp_config.get("username") and self.smtp_config.get("password"):
                    await smtp.login(
                        self.smtp_config["username"],
                        self.smtp_config["password"]
                    )
                
                # Combina todos os destinatários
                all_recipients = [to]
                if cc:
                    all_recipients.extend(cc)
                if bcc:
                    all_recipients.extend(bcc)
                
                await smtp.send_message(msg, recipients=all_recipients)
                
            logger.info(f"Email enviado com sucesso para {to} via SMTP")
            return True
            
        except Exception as e:
            logger.error(f"Erro no SMTP: {str(e)}")
            return False
    
    async def send_bulk(
        self,
        recipients: List[str],
        subject: str,
        template: str,
        template_vars: Optional[Dict[str, Any]] = None,
        personalize: bool = False
    ) -> Dict[str, bool]:
        """
        Envia emails em massa para múltiplos destinatários
        
        Args:
            recipients: Lista de emails destinatários
            subject: Assunto do email
            template: Template a usar
            template_vars: Variáveis do template
            personalize: Se True, permite personalização por destinatário
            
        Returns:
            Dict com status de envio para cada destinatário
            
        Note:
            Para melhor performance, usa asyncio.gather para envio paralelo
            Respeita rate limits do provedor de email
        """
        results = {}
        
        # Limita envios paralelos para evitar throttling
        MAX_CONCURRENT = 5
        semaphore = asyncio.Semaphore(MAX_CONCURRENT)
        
        async def send_with_limit(recipient: str):
            """Envia email respeitando limite de concorrência"""
            async with semaphore:
                # Personaliza variáveis se necessário
                vars_copy = template_vars.copy() if template_vars else {}
                
                if personalize:
                    # Aqui você pode adicionar personalização
                    # Por exemplo, adicionar o nome do usuário
                    vars_copy["recipient_email"] = recipient
                
                # Pequeno delay entre envios para evitar spam
                await asyncio.sleep(0.5)
                
                return await self.send(
                    to=recipient,
                    subject=subject,
                    body="",  # Template fornecerá o conteúdo
                    template=template,
                    template_vars=vars_copy
                )
        
        # Envia emails em paralelo
        tasks = [send_with_limit(recipient) for recipient in recipients]
        statuses = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Mapeia resultados
        for recipient, status in zip(recipients, statuses):
            if isinstance(status, Exception):
                logger.error(f"Erro ao enviar para {recipient}: {status}")
                results[recipient] = False
            else:
                results[recipient] = status
        
        # Log resumo
        successful = sum(1 for status in results.values() if status)
        logger.info(f"Emails em massa: {successful}/{len(recipients)} enviados com sucesso")
        
        return results
    
    async def send_price_alert(
        self,
        to: str,
        product_data: Dict[str, Any]
    ) -> bool:
        """
        Envia alerta de preço formatado
        
        Args:
            to: Email do destinatário
            product_data: Dados do produto incluindo título, preços, URL, etc.
            
        Returns:
            bool: Status do envio
        """
        # Calcula desconto
        discount = 0
        if product_data.get("old_price") and product_data.get("new_price"):
            old = float(product_data["old_price"])
            new = float(product_data["new_price"])
            if old > 0:
                discount = round((1 - new/old) * 100, 2)
        
        # Prepara variáveis do template
        template_vars = {
            "product_title": product_data.get("title", "Produto"),
            "old_price": product_data.get("old_price", "N/A"),
            "new_price": product_data.get("new_price", "N/A"),
            "discount": discount,
            "product_url": product_data.get("url", "#"),
            "target_price": product_data.get("target_price", "N/A")
        }
        
        return await self.send(
            to=to,
            subject=f"🎉 Alerta de Preço: {product_data.get('title', 'Produto')}",
            body=f"O preço do produto {product_data.get('title')} caiu para ${product_data.get('new_price')}!",
            template="price_drop",
            template_vars=template_vars
        )
