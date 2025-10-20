"""
Product models for Amazon scraper
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, HttpUrl, validator
from bson import ObjectId

class ProductStatus(str, Enum):
    """Product availability status"""
    IN_STOCK = "in_stock"
    OUT_OF_STOCK = "out_of_stock"
    LIMITED_STOCK = "limited_stock"
    PRE_ORDER = "pre_order"
    DISCONTINUED = "discontinued"
    UNKNOWN = "unknown"

class PriceHistory(BaseModel):
    """Price history entry"""
    price: float
    currency: str = "USD"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    is_discounted: bool = False
    discount_percentage: Optional[float] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class ProductImage(BaseModel):
    """Product image details"""
    url: HttpUrl
    alt_text: Optional[str] = None
    is_primary: bool = False
    width: Optional[int] = None
    height: Optional[int] = None

class ProductReview(BaseModel):
    """Product review summary"""
    average_rating: float = Field(ge=0, le=5)
    total_reviews: int = Field(ge=0)
    rating_distribution: Dict[int, int] = Field(default_factory=dict)
    
    @validator("rating_distribution")
    def validate_rating_distribution(cls, v):
        valid_keys = {1, 2, 3, 4, 5}
        if not all(k in valid_keys for k in v.keys()):
            raise ValueError("Rating distribution keys must be 1-5")
        return v

class ShippingInfo(BaseModel):
    """Shipping information"""
    is_prime: bool = False
    free_shipping: bool = False
    estimated_delivery: Optional[str] = None
    shipping_cost: Optional[float] = None
    ships_from: Optional[str] = None
    sold_by: Optional[str] = None

class Product(BaseModel):
    """Complete product model"""
    # Identifiers
    id: Optional[str] = Field(default=None, alias="_id")
    asin: str = Field(..., regex="^[A-Z0-9]{10}$")
    url: HttpUrl
    
    # Basic Info
    title: str = Field(..., min_length=1, max_length=500)
    brand: Optional[str] = None
    category: List[str] = Field(default_factory=list)
    description: Optional[str] = None
    
    # Pricing
    current_price: float = Field(..., ge=0)
    original_price: Optional[float] = Field(None, ge=0)
    currency: str = Field(default="USD", regex="^[A-Z]{3}$")
    price_history: List[PriceHistory] = Field(default_factory=list)
    
    # Availability
    status: ProductStatus = ProductStatus.UNKNOWN
    quantity_available: Optional[int] = None
    
    # Images
    images: List[ProductImage] = Field(default_factory=list)
    
    # Reviews
    reviews: Optional[ProductReview] = None
    
    # Shipping
    shipping: Optional[ShippingInfo] = None
    
    # Seller Info
    seller_name: Optional[str] = None
    seller_rating: Optional[float] = Field(None, ge=0, le=5)
    is_amazon_seller: bool = False
    
    # Technical Details
    specifications: Dict[str, Any] = Field(default_factory=dict)
    features: List[str] = Field(default_factory=list)
    
    # Metadata
    scraped_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_checked: datetime = Field(default_factory=datetime.utcnow)
    scrape_count: int = Field(default=1)
    
    # Competition
    competitors: List[str] = Field(default_factory=list)  # ASINs of similar products
    rank_in_category: Optional[int] = None
    
    # Flags
    is_tracked: bool = Field(default=False)
    is_favorite: bool = Field(default=False)
    has_alert: bool = Field(default=False)
    alert_price: Optional[float] = None
    
    # AI Analysis
    ai_summary: Optional[str] = None
    sentiment_score: Optional[float] = Field(None, ge=-1, le=1)
    quality_score: Optional[float] = Field(None, ge=0, le=100)
    value_score: Optional[float] = Field(None, ge=0, le=100)
    
    class Config:
        populate_by_name = True
        use_enum_values = True
        json_encoders = {
            ObjectId: str,
            datetime: lambda v: v.isoformat()
        }
        schema_extra = {
            "example": {
                "asin": "B08N5WRWNW",
                "url": "https://www.amazon.com/dp/B08N5WRWNW",
                "title": "Echo Echo (4th Echo generation)",
                "brand": "Amazon",
                "current_price": 99.99,
                "status": "in_stock"
            }
        }
    
    @validator("original_price")
    def validate_original_price(cls, v, values):
        if v and "current_price" in values:
            if v < values["current_price"]:
                raise ValueError("Original price cannot be less than current price")
        return v
    
    @validator("updated_at", always=True)
    def update_timestamp(cls, v):
        return datetime.utcnow()
    
    def calculate_discount(self) -> Optional[float]:
        """Calculate discount percentage"""
        if self.original_price and self.original_price > self.current_price:
            return round((1 - self.current_price / self.original_price) * 100, 2)
        return None
    
    def is_price_dropped(self, threshold: float = 0.1) -> bool:
        """Check if price dropped by threshold percentage"""
        if len(self.price_history) < 2:
            return False
        
        previous_price = self.price_history[-2].price
        current_price = self.price_history[-1].price
        
        if previous_price > 0:
            drop_percentage = (previous_price - current_price) / previous_price
            return drop_percentage >= threshold
        return False
    
    def to_mongo(self) -> dict:
        """Convert to MongoDB document"""
        data = self.dict(by_alias=True, exclude_none=True)
        if data.get("_id") and isinstance(data["_id"], str):
            data["_id"] = ObjectId(data["_id"])
        return data
    
    @classmethod
    def from_mongo(cls, data: dict) -> "Product":
        """Create from MongoDB document"""
        if data.get("_id"):
            data["_id"] = str(data["_id"])
        return cls(**data)
