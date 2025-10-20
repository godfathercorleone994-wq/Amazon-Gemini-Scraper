"""
Notification models
"""
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, EmailStr

class NotificationType(str, Enum):
    """Types of notifications"""
    PRICE_DROP = "price_drop"
    BACK_IN_STOCK = "back_in_stock"
    LOW_STOCK = "low_stock"
    NEW_REVIEW = "new_review"
    COMPETITOR_ALERT = "competitor_alert"
    SCRAPING_ERROR = "scraping_error"
    DAILY_SUMMARY = "daily_summary"
    CUSTOM = "custom"

class NotificationChannel(str, Enum):
    """Notification delivery channels"""
    EMAIL = "email"
    TELEGRAM = "telegram"
    DISCORD = "discord"
    WEBHOOK = "webhook"
    SMS = "sms"
    IN_APP = "in_app"

class NotificationPriority(str, Enum):
    """Notification priority levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"

class NotificationRecipient(BaseModel):
    """Notification recipient details"""
    channel: NotificationChannel
    address: str  # email, phone, chat_id, webhook_url
    name: Optional[str] = None
    preferences: Dict[str, Any] = Field(default_factory=dict)

class Notification(BaseModel):
    """Notification model"""
    # Identifiers
    id: Optional[str] = Field(default=None, alias="_id")
    
    # Type & Content
    type: NotificationType
    title: str
    message: str
    data: Dict[str, Any] = Field(default_factory=dict)
    
    # Recipients
    recipients: List[NotificationRecipient]
    
    # Priority & Scheduling
    priority: NotificationPriority = NotificationPriority.MEDIUM
    scheduled_for: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    
    # Status
    is_sent: bool = False
    sent_at: Optional[datetime] = None
    is_read: bool = False
    read_at: Optional[datetime] = None
    
    # Delivery
    delivery_attempts: int = 0
    max_delivery_attempts: int = 3
    delivery_errors: List[str] = Field(default_factory=list)
    delivered_channels: List[NotificationChannel] = Field(default_factory=list)
    
    # Related Entity
    product_asin: Optional[str] = None
    user_id: Optional[str] = None
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Template
    template_id: Optional[str] = None
    template_variables: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        use_enum_values = True
        populate_by_name = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
    
    def mark_sent(self, channel: NotificationChannel):
        """Mark notification as sent for a channel"""
        self.delivered_channels.append(channel)
        if not self.is_sent:
            self.is_sent = True
            self.sent_at = datetime.utcnow()
    
    def mark_read(self):
        """Mark notification as read"""
        self.is_read = True
        self.read_at = datetime.utcnow()
    
    def add_delivery_error(self, error: str):
        """Add delivery error"""
        self.delivery_errors.append(error)
        self.delivery_attempts += 1
    
    def should_retry(self) -> bool:
        """Check if notification should be retried"""
        return (
            not self.is_sent and
            self.delivery_attempts < self.max_delivery_attempts and
            (not self.expires_at or datetime.utcnow() < self.expires_at)
      )
