"""
Notification API routes
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from typing import List, Optional
from pydantic import BaseModel, Field, EmailStr
from datetime import datetime

from storage.mongodb_client import get_mongodb
from features.notifications.email_sender import EmailSender
from features.notifications.telegram_bot import TelegramBot
from features.notifications.webhook_manager import WebhookManager
from models.notification import Notification, NotificationType, NotificationChannel, NotificationPriority
from utils.logger import logger
from config.settings import settings

router = APIRouter()

# ==================== Request/Response Models ====================

class CreateNotificationRequest(BaseModel):
    """Create notification request"""
    type: NotificationType = Field(..., description="Notification type")
    title: str = Field(..., min_length=1, max_length=200)
    message: str = Field(..., min_length=1, max_length=1000)
    channels: List[NotificationChannel] = Field(..., min_items=1)
    recipients: List[str] = Field(..., min_items=1, description="Email addresses, chat IDs, etc.")
    priority: NotificationPriority = Field(default=NotificationPriority.MEDIUM)
    product_asin: Optional[str] = Field(None, pattern="^[A-Z0-9]{10}$")
    scheduled_for: Optional[datetime] = None
    
    class Config:
        schema_extra = {
            "example": {
                "type": "price_drop",
                "title": "Price Drop Alert!",
                "message": "The product you're tracking has dropped in price",
                "channels": ["email", "telegram"],
                "recipients": ["user@example.com", "123456789"],
                "priority": "high",
                "product_asin": "B08N5WRWNW"
            }
        }

class PriceAlertRequest(BaseModel):
    """Price alert configuration"""
    asin: str = Field(..., pattern="^[A-Z0-9]{10}$")
    target_price: float = Field(..., gt=0)
    email: Optional[EmailStr] = None
    telegram_chat_id: Optional[str] = None
    
    class Config:
        schema_extra = {
            "example": {
                "asin": "B08N5WRWNW",
                "target_price": 79.99,
                "email": "user@example.com"
            }
        }

class WebhookRequest(BaseModel):
    """Webhook configuration"""
    url: str = Field(..., description="Webhook URL")
    events: List[str] = Field(..., min_items=1, description="Events to subscribe to")
    secret: Optional[str] = Field(None, description="Webhook secret for validation")
    
    class Config:
        schema_extra = {
            "example": {
                "url": "https://example.com/webhook",
                "events": ["price_drop", "back_in_stock"],
                "secret": "webhook_secret_123"
            }
        }

# ==================== Background Tasks ====================

async def send_notification_task(notification: Notification):
    """Background task to send notification"""
    try:
        mongodb = await get_mongodb()
        
        # Send based on channels
        for recipient in notification.recipients:
            try:
                if recipient.channel == NotificationChannel.EMAIL:
                    email_sender = EmailSender()
                    await email_sender.send(
                        to=recipient.address,
                        subject=notification.title,
                        body=notification.message
                    )
                    notification.mark_sent(NotificationChannel.EMAIL)
                    
                elif recipient.channel == NotificationChannel.TELEGRAM:
                    telegram_bot = TelegramBot()
                    await telegram_bot.send_message(
                        chat_id=recipient.address,
                        text=f"*{notification.title}*\n\n{notification.message}",
                        parse_mode="Markdown"
                    )
                    notification.mark_sent(NotificationChannel.TELEGRAM)
                    
                elif recipient.channel == NotificationChannel.WEBHOOK:
                    webhook_manager = WebhookManager()
                    await webhook_manager.send_webhook(
                        url=recipient.address,
                        data={
                            "type": notification.type,
                            "title": notification.title,
                            "message": notification.message,
                            "data": notification.data
                        }
                    )
                    notification.mark_sent(NotificationChannel.WEBHOOK)
                    
            except Exception as e:
                logger.error(f"Failed to send notification via {recipient.channel}: {str(e)}")
                notification.add_delivery_error(str(e))
        
        # Update notification in database
        await mongodb.save_notification(notification)
        
    except Exception as e:
        logger.error(f"Notification task failed: {str(e)}")

async def check_price_alerts_task():
    """Background task to check price alerts"""
    try:
        mongodb = await get_mongodb()
        
        # Get products with price alerts
        products_with_alerts = await mongodb.get_products_with_price_alerts()
        
        for product in products_with_alerts:
            # Create notification
            notification = Notification(
                type=NotificationType.PRICE_DROP,
                title=f"Price Alert: {product.title}",
                message=f"Price dropped to ${product.current_price} (target: ${product.alert_price})",
                recipients=[],  # Will be filled from alert settings
                priority=NotificationPriority.HIGH,
                product_asin=product.asin,
                data={
                    "current_price": product.current_price,
                    "alert_price": product.alert_price,
                    "discount": product.calculate_discount()
                }
            )
            
            # Save and send notification
            await mongodb.save_notification(notification)
            
    except Exception as e:
        logger.error(f"Price alert check failed: {str(e)}")

# ==================== Endpoints ====================

@router.post("/create")
async def create_notification(
    request: CreateNotificationRequest,
    background_tasks: BackgroundTasks
):
    """
    Create and send a notification
    
    - **type**: Type of notification
    - **title**: Notification title
    - **message**: Notification message
    - **channels**: Delivery channels (email, telegram, etc.)
    - **recipients**: List of recipient addresses
    - **priority**: Notification priority
    - **product_asin**: Related product ASIN (optional)
    - **scheduled_for**: Schedule for later (optional)
    """
    try:
        # Create notification
        notification = Notification(
            type=request.type,
            title=request.title,
            message=request.message,
            priority=request.priority,
            product_asin=request.product_asin,
            scheduled_for=request.scheduled_for,
            recipients=[
                {
                    "channel": channel,
                    "address": recipient
                }
                for channel in request.channels
                for recipient in request.recipients
            ]
        )
        
        # Save to database
        mongodb = await get_mongodb()
        notification_id = await mongodb.save_notification(notification)
        
        # Send immediately if not scheduled
        if not request.scheduled_for or request.scheduled_for <= datetime.utcnow():
            background_tasks.add_task(send_notification_task, notification)
        
        return {
            "success": True,
            "notification_id": notification_id,
            "message": "Notification created successfully"
        }
        
    except Exception as e:
        logger.error(f"Error creating notification: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/price-alert")
async def set_price_alert(request: PriceAlertRequest):
    """
    Set price alert for a product
    
    - **asin**: Product ASIN
    - **target_price**: Target price for alert
    - **email**: Email for notifications (optional)
    - **telegram_chat_id**: Telegram chat ID (optional)
    """
    try:
        mongodb = await get_mongodb()
        
        # Get product
        product = await mongodb.get_product_by_asin(request.asin)
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        
        # Update product with alert
        product.has_alert = True
        product.alert_price = request.target_price
        
        await mongodb.save_product(product)
        
        # Create notification preferences
        recipients = []
        if request.email:
            recipients.append({
                "channel": NotificationChannel.EMAIL,
                "address": request.email
            })
        if request.telegram_chat_id:
            recipients.append({
                "channel": NotificationChannel.TELEGRAM,
                "address": request.telegram_chat_id
            })
        
        # Save alert configuration
        # In production, you'd save this to a separate alerts collection
        
        return {
            "success": True,
            "message": f"Price alert set for {product.title} at ${request.target_price}",
            "current_price": product.current_price,
            "target_price": request.target_price
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error setting price alert: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/webhook/subscribe")
async def subscribe_webhook(request: WebhookRequest):
    """
    Subscribe to webhook notifications
    
    - **url**: Webhook endpoint URL
    - **events**: List of events to subscribe to
    - **secret**: Optional secret for webhook validation
    """
    try:
        # Validate webhook URL
        webhook_manager = WebhookManager()
        is_valid = await webhook_manager.validate_webhook(request.url)
        
        if not is_valid:
            raise HTTPException(status_code=400, detail="Invalid webhook URL")
        
        # Save webhook subscription
        # In production, you'd save this to a webhooks collection
        subscription = {
            "url": request.url,
            "events": request.events,
            "secret": request.secret,
            "created_at": datetime.utcnow(),
            "active": True
        }
        
        return {
            "success": True,
            "message": "Webhook subscribed successfully",
            "subscription": subscription
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error subscribing webhook: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/list")
async def list_notifications(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    is_sent: Optional[bool] = None,
    type: Optional[NotificationType] = None
):
    """
    List notifications
    
    - **skip**: Number of notifications to skip
    - **limit**: Number of notifications to return
    - **is_sent**: Filter by sent status
    - **type**: Filter by notification type
    """
    try:
        mongodb = await get_mongodb()
        
        # Build filters
        filters = {}
        if is_sent is not None:
            filters["is_sent"] = is_sent
        if type:
            filters["type"] = type
        
        # Get notifications
        notifications = await mongodb.notifications.find(filters)\
            .skip(skip)\
            .limit(limit)\
            .sort("created_at", -1)\
            .to_list(limit)
        
        return {
            "success": True,
            "count": len(notifications),
            "notifications": notifications
        }
        
    except Exception as e:
        logger.error(f"Error listing notifications: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/pending")
async def get_pending_notifications():
    """
    Get pending notifications that need to be sent
    """
    try:
        mongodb = await get_mongodb()
        
        pending = await mongodb.get_pending_notifications()
        
        return {
            "success": True,
            "count": len(pending),
            "notifications": [n.dict() for n in pending]
        }
        
    except Exception as e:
        logger.error(f"Error getting pending notifications: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/test")
async def test_notification(
    channel: NotificationChannel = Query(..., description="Channel to test"),
    recipient: str = Query(..., description="Recipient address")
):
    """
    Send test notification
    
    - **channel**: Notification channel (email, telegram, etc.)
    - **recipient**: Recipient address
    """
    try:
        test_message = f"Test notification from {settings.app_name}"
        
        if channel == NotificationChannel.EMAIL:
            email_sender = EmailSender()
            await email_sender.send(
                to=recipient,
                subject="Test Notification",
                body=test_message
            )
        elif channel == NotificationChannel.TELEGRAM:
            telegram_bot = TelegramBot()
            await telegram_bot.send_message(
                chat_id=recipient,
                text=test_message
            )
        else:
            raise HTTPException(status_code=400, detail=f"Channel {channel} not supported for testing")
        
        return {
            "success": True,
            "message": f"Test notification sent to {recipient} via {channel}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending test notification: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
