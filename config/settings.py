"""
Configuration settings for Amazon Gemini Scraper
"""
from typing import Optional, List
from pydantic import BaseSettings, Field, validator
from functools import lru_cache
import os
from pathlib import Path

class Settings(BaseSettings):
    """Application settings with validation"""
    
    # Application
    app_name: str = Field(default="Amazon-Gemini-Scraper")
    app_version: str = Field(default="1.0.0")
    environment: str = Field(default="development")
    debug: bool = Field(default=False)
    secret_key: str = Field(default="change-me-in-production")
    api_prefix: str = Field(default="/api/v1")
    
    # Server
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000)
    workers: int = Field(default=4)
    reload: bool = Field(default=False)
    
    @validator("port", pre=True)
    def parse_port(cls, v):
        """Parse PORT from environment (for Render deployment)"""
        if isinstance(v, str):
            return int(v)
        return v
    
    # Database
    mongodb_atlas_uri: str = Field(default="mongodb://localhost:27017")
    mongodb_database: str = Field(default="amazon_scraper")
    mongodb_max_connections: int = Field(default=100)
    mongodb_min_connections: int = Field(default=10)
    
    # Redis
    redis_url: str = Field(default="redis://localhost:6379/0")
    redis_ttl: int = Field(default=3600)  # 1 hour
    redis_max_connections: int = Field(default=50)
    
    # AI APIs
    gemini_api_key: Optional[str] = Field(default=None)
    openai_api_key: Optional[str] = Field(default=None)
    huggingface_api_key: Optional[str] = Field(default=None)
    ai_timeout: int = Field(default=30)
    ai_max_retries: int = Field(default=3)
    ai_model_gemini: str = Field(default="gemini-pro")
    ai_model_openai: str = Field(default="gpt-4-turbo-preview")
    
    # AWS
    aws_access_key_id: Optional[str] = Field(default=None)
    aws_secret_access_key: Optional[str] = Field(default=None)
    aws_region: str = Field(default="us-east-1")
    s3_bucket_name: Optional[str] = Field(default=None)
    
    # Notifications
    telegram_bot_token: Optional[str] = Field(default=None)
    telegram_chat_ids: List[str] = Field(default_factory=list)
    sendgrid_api_key: Optional[str] = Field(default=None)
    email_from: str = Field(default="noreply@scraper.com")
    email_admin: List[str] = Field(default_factory=list)
    discord_webhook_url: Optional[str] = Field(default=None)
    
    # Rate Limiting
    api_rate_limit: int = Field(default=100)
    api_rate_limit_period: int = Field(default=60)  # seconds
    scraper_rate_limit: int = Field(default=10)  # requests per minute
    
    # Scraping
    max_concurrent_scrapers: int = Field(default=5)
    scraper_timeout: int = Field(default=30000)  # milliseconds
    scraper_headless: bool = Field(default=True)
    use_proxy: bool = Field(default=False)
    proxy_list: List[str] = Field(default_factory=list)
    user_agent_rotation: bool = Field(default=True)
    max_retries: int = Field(default=3)
    retry_delay: int = Field(default=5)  # seconds
    
    # Celery
    celery_broker_url: str = Field(default="redis://localhost:6379/1")
    celery_result_backend: str = Field(default="redis://localhost:6379/2")
    celery_task_time_limit: int = Field(default=300)  # 5 minutes
    celery_task_soft_time_limit: int = Field(default=240)  # 4 minutes
    celery_worker_concurrency: int = Field(default=4)
    
    # Monitoring
    sentry_dsn: Optional[str] = Field(default=None)
    prometheus_enabled: bool = Field(default=True)
    log_level: str = Field(default="INFO")
    log_file: str = Field(default="logs/app.log")
    
    # Security
    jwt_algorithm: str = Field(default="HS256")
    access_token_expire_minutes: int = Field(default=30)
    refresh_token_expire_days: int = Field(default=7)
    cors_origins: List[str] = Field(default=["*"])
    cors_credentials: bool = Field(default=True)
    cors_methods: List[str] = Field(default=["*"])
    cors_headers: List[str] = Field(default=["*"])
    
    # File Storage
    upload_max_size: int = Field(default=10485760)  # 10MB
    allowed_extensions: List[str] = Field(default=[".jpg", ".png", ".pdf", ".xlsx"])
    temp_folder: str = Field(default="tmp/")
    
    # Features
    enable_ml_features: bool = Field(default=True)
    enable_notifications: bool = Field(default=True)
    enable_dashboard: bool = Field(default=True)
    enable_webhooks: bool = Field(default=True)
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"
    
    @validator("proxy_list", pre=True)
    def parse_proxy_list(cls, v):
        if isinstance(v, str):
            return [p.strip() for p in v.split(",") if p.strip()]
        return v
    
    @validator("telegram_chat_ids", pre=True)
    def parse_telegram_chat_ids(cls, v):
        if isinstance(v, str):
            return [id.strip() for id in v.split(",") if id.strip()]
        return v
    
    @validator("email_admin", pre=True)
    def parse_email_admin(cls, v):
        if isinstance(v, str):
            return [email.strip() for email in v.split(",") if email.strip()]
        return v
    
    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"
    
    @property
    def is_development(self) -> bool:
        return self.environment.lower() == "development"
    
    @property
    def database_url(self) -> str:
        return f"{self.mongodb_atlas_uri}/{self.mongodb_database}"
    
    @property
    def log_dir(self) -> Path:
        return Path(self.log_file).parent
    
    def get_ai_api_key(self, provider: str = "gemini") -> Optional[str]:
        """Get API key for specified AI provider"""
        providers = {
            "gemini": self.gemini_api_key,
            "openai": self.openai_api_key,
            "huggingface": self.huggingface_api_key
        }
        return providers.get(provider.lower())
    
    def has_ai_provider(self, provider: str) -> bool:
        """Check if AI provider is configured"""
        return self.get_ai_api_key(provider) is not None

@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()

# Create settings instance
settings = get_settings()
