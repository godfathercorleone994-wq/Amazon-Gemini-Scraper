"""
MongoDB client for data persistence
"""
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase, AsyncIOMotorCollection
from pymongo import IndexModel, ASCENDING, DESCENDING, TEXT
from pymongo.errors import DuplicateKeyError, ConnectionFailure
import asyncio

from config.settings import settings
from utils.logger import logger
from models.product import Product
from models.extraction_result import ExtractionResult
from models.notification import Notification

class MongoDBClient:
    """Async MongoDB client for data operations"""
    
    def __init__(self):
        self.client: Optional[AsyncIOMotorClient] = None
        self.db: Optional[AsyncIOMotorDatabase] = None
        self._initialized = False
        
        # Collection references
        self.products: Optional[AsyncIOMotorCollection] = None
        self.extraction_results: Optional[AsyncIOMotorCollection] = None
        self.notifications: Optional[AsyncIOMotorCollection] = None
        self.price_history: Optional[AsyncIOMotorCollection] = None
        self.analytics: Optional[AsyncIOMotorCollection] = None
    
    async def connect(self):
        """Connect to MongoDB"""
        if self._initialized:
            return
        
        try:
            logger.info("Connecting to MongoDB...")
            
            self.client = AsyncIOMotorClient(
                settings.mongodb_atlas_uri,
                maxPoolSize=settings.mongodb_max_connections,
                minPoolSize=settings.mongodb_min_connections,
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=10000,
                socketTimeoutMS=30000
            )
            
            # Test connection
            await self.client.admin.command('ping')
            
            # Get database
            self.db = self.client[settings.mongodb_database]
            
            # Initialize collections
            self.products = self.db.products
            self.extraction_results = self.db.extraction_results
            self.notifications = self.db.notifications
            self.price_history = self.db.price_history
            self.analytics = self.db.analytics
            
            # Create indexes
            await self._create_indexes()
            
            self._initialized = True
            logger.info("MongoDB connected successfully")
            
        except ConnectionFailure as e:
            logger.error(f"Failed to connect to MongoDB: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"MongoDB initialization error: {str(e)}")
            raise
    
    async def disconnect(self):
        """Disconnect from MongoDB"""
        if self.client:
            self.client.close()
            self._initialized = False
            logger.info("MongoDB disconnected")
    
    async def _create_indexes(self):
        """Create database indexes for performance"""
        logger.info("Creating MongoDB indexes...")
        
        # Products collection indexes
        products_indexes = [
            IndexModel([("asin", ASCENDING)], unique=True, name="asin_unique"),
            IndexModel([("title", TEXT)], name="title_text"),
            IndexModel([("brand", ASCENDING)], name="brand_idx"),
            IndexModel([("current_price", ASCENDING)], name="price_idx"),
            IndexModel([("status", ASCENDING)], name="status_idx"),
            IndexModel([("scraped_at", DESCENDING)], name="scraped_at_idx"),
            IndexModel([("is_tracked", ASCENDING)], name="tracked_idx"),
            IndexModel([("category", ASCENDING)], name="category_idx"),
            IndexModel([
                ("current_price", ASCENDING),
                ("status", ASCENDING)
            ], name="price_status_compound"),
        ]
        await self.products.create_indexes(products_indexes)
        
        # Extraction results indexes
        extraction_indexes = [
            IndexModel([("task_id", ASCENDING)], unique=True, name="task_id_unique"),
            IndexModel([("asin", ASCENDING)], name="asin_idx"),
            IndexModel([("status", ASCENDING)], name="status_idx"),
            IndexModel([("started_at", DESCENDING)], name="started_at_idx"),
        ]
        await self.extraction_results.create_indexes(extraction_indexes)
        
        # Notifications indexes
        notification_indexes = [
            IndexModel([("type", ASCENDING)], name="type_idx"),
            IndexModel([("is_sent", ASCENDING)], name="is_sent_idx"),
            IndexModel([("scheduled_for", ASCENDING)], name="scheduled_idx"),
            IndexModel([("product_asin", ASCENDING)], name="product_asin_idx"),
            IndexModel([("created_at", DESCENDING)], name="created_at_idx"),
        ]
        await self.notifications.create_indexes(notification_indexes)
        
        # Price history indexes
        price_history_indexes = [
            IndexModel([("asin", ASCENDING), ("timestamp", DESCENDING)], name="asin_time_compound"),
            IndexModel([("timestamp", DESCENDING)], name="timestamp_idx"),
        ]
        await self.price_history.create_indexes(price_history_indexes)
        
        logger.info("MongoDB indexes created successfully")
    
    # ==================== Product Operations ====================
    
    async def save_product(self, product: Product) -> str:
        """Save or update product"""
        try:
            product_dict = product.to_mongo()
            
            # Upsert based on ASIN
            result = await self.products.update_one(
                {"asin": product.asin},
                {"$set": product_dict},
                upsert=True
            )
            
            if result.upserted_id:
                logger.info(f"Product created: {product.asin}")
                return str(result.upserted_id)
            else:
                logger.info(f"Product updated: {product.asin}")
                # Get existing document ID
                doc = await self.products.find_one({"asin": product.asin})
                return str(doc["_id"]) if doc else None
                
        except DuplicateKeyError:
            logger.warning(f"Duplicate product ASIN: {product.asin}")
            raise
        except Exception as e:
            logger.error(f"Error saving product: {str(e)}")
            raise
    
    async def get_product_by_asin(self, asin: str) -> Optional[Product]:
        """Get product by ASIN"""
        try:
            doc = await self.products.find_one({"asin": asin})
            if doc:
                return Product.from_mongo(doc)
            return None
        except Exception as e:
            logger.error(f"Error getting product: {str(e)}")
            return None
    
    async def get_products(
        self,
        skip: int = 0,
        limit: int = 100,
        filters: Optional[Dict[str, Any]] = None,
        sort_by: str = "scraped_at",
        sort_order: int = DESCENDING
    ) -> List[Product]:
        """Get products with filters and pagination"""
        try:
            query = filters or {}
            
            cursor = self.products.find(query).skip(skip).limit(limit).sort(sort_by, sort_order)
            
            products = []
            async for doc in cursor:
                products.append(Product.from_mongo(doc))
            
            return products
            
        except Exception as e:
            logger.error(f"Error getting products: {str(e)}")
            return []
    
    async def search_products(self, search_text: str, limit: int = 50) -> List[Product]:
        """Search products by text"""
        try:
            cursor = self.products.find(
                {"$text": {"$search": search_text}}
            ).limit(limit)
            
            products = []
            async for doc in cursor:
                products.append(Product.from_mongo(doc))
            
            return products
            
        except Exception as e:
            logger.error(f"Error searching products: {str(e)}")
            return []
    
    async def delete_product(self, asin: str) -> bool:
        """Delete product by ASIN"""
        try:
            result = await self.products.delete_one({"asin": asin})
            return result.deleted_count > 0
        except Exception as e:
            logger.error(f"Error deleting product: {str(e)}")
            return False
    
    async def update_product_price(self, asin: str, new_price: float, currency: str = "USD") -> bool:
        """Update product price and add to history"""
        try:
            # Get current product
            product = await self.get_product_by_asin(asin)
            if not product:
                return False
            
            # Update price
            old_price = product.current_price
            
            result = await self.products.update_one(
                {"asin": asin},
                {
                    "$set": {
                        "current_price": new_price,
                        "updated_at": datetime.utcnow()
                    },
                    "$push": {
                        "price_history": {
                            "price": new_price,
                            "currency": currency,
                            "timestamp": datetime.utcnow(),
                            "is_discounted": new_price < old_price
                        }
                    }
                }
            )
            
            # Also save to price history collection
            await self.save_price_history(asin, new_price, currency)
            
            return result.modified_count > 0
            
        except Exception as e:
            logger.error(f"Error updating product price: {str(e)}")
            return False
    
    async def get_tracked_products(self) -> List[Product]:
        """Get all tracked products"""
        return await self.get_products(filters={"is_tracked": True}, limit=1000)
    
    async def get_products_with_price_alerts(self) -> List[Product]:
        """Get products that have price alerts set"""
        try:
            cursor = self.products.find({
                "has_alert": True,
                "alert_price": {"$exists": True}
            })
            
            products = []
            async for doc in cursor:
                product = Product.from_mongo(doc)
                # Check if current price is below alert price
                if product.current_price <= product.alert_price:
                    products.append(product)
            
            return products
            
        except Exception as e:
            logger.error(f"Error getting products with alerts: {str(e)}")
            return []
    
    # ==================== Price History Operations ====================
    
    async def save_price_history(self, asin: str, price: float, currency: str = "USD"):
        """Save price history entry"""
        try:
            entry = {
                "asin": asin,
                "price": price,
                "currency": currency,
                "timestamp": datetime.utcnow()
            }
            await self.price_history.insert_one(entry)
        except Exception as e:
            logger.error(f"Error saving price history: {str(e)}")
    
    async def get_price_history(
        self,
        asin: str,
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """Get price history for product"""
        try:
            start_date = datetime.utcnow() - timedelta(days=days)
            
            cursor = self.price_history.find({
                "asin": asin,
                "timestamp": {"$gte": start_date}
            }).sort("timestamp", ASCENDING)
            
            history = []
            async for entry in cursor:
                history.append({
                    "price": entry["price"],
                    "currency": entry.get("currency", "USD"),
                    "timestamp": entry["timestamp"]
                })
            
            return history
            
        except Exception as e:
            logger.error(f"Error getting price history: {str(e)}")
            return []
    
    # ==================== Extraction Results Operations ====================
    
    async def save_extraction_result(self, result: ExtractionResult) -> str:
        """Save extraction result"""
        try:
            result_dict = result.dict(by_alias=True, exclude_none=True)
            
            inserted = await self.extraction_results.insert_one(result_dict)
            logger.info(f"Extraction result saved: {result.task_id}")
            
            return str(inserted.inserted_id)
            
        except Exception as e:
            logger.error(f"Error saving extraction result: {str(e)}")
            raise
    
    async def get_extraction_result(self, task_id: str) -> Optional[ExtractionResult]:
        """Get extraction result by task ID"""
        try:
            doc = await self.extraction_results.find_one({"task_id": task_id})
            if doc:
                return ExtractionResult(**doc)
            return None
        except Exception as e:
            logger.error(f"Error getting extraction result: {str(e)}")
            return None
    
    async def get_recent_extractions(self, limit: int = 100) -> List[ExtractionResult]:
        """Get recent extraction results"""
        try:
            cursor = self.extraction_results.find().sort("started_at", DESCENDING).limit(limit)
            
            results = []
            async for doc in cursor:
                results.append(ExtractionResult(**doc))
            
            return results
            
        except Exception as e:
            logger.error(f"Error getting recent extractions: {str(e)}")
            return []
    
    # ==================== Notification Operations ====================
    
    async def save_notification(self, notification: Notification) -> str:
        """Save notification"""
        try:
            notif_dict = notification.dict(by_alias=True, exclude_none=True)
            
            inserted = await self.notifications.insert_one(notif_dict)
            logger.info(f"Notification saved: {notification.type}")
            
            return str(inserted.inserted_id)
            
        except Exception as e:
            logger.error(f"Error saving notification: {str(e)}")
            raise
    
    async def get_pending_notifications(self) -> List[Notification]:
        """Get notifications that need to be sent"""
        try:
            now = datetime.utcnow()
            
            cursor = self.notifications.find({
                "is_sent": False,
                "$or": [
                    {"scheduled_for": None},
                    {"scheduled_for": {"$lte": now}}
                ],
                "$or": [
                    {"expires_at": None},
                    {"expires_at": {"$gt": now}}
                ]
            })
            
            notifications = []
            async for doc in cursor:
                notifications.append(Notification(**doc))
            
            return notifications
            
        except Exception as e:
            logger.error(f"Error getting pending notifications: {str(e)}")
            return []
    
    async def mark_notification_sent(self, notification_id: str, channel: str) -> bool:
        """Mark notification as sent"""
        try:
            result = await self.notifications.update_one(
                {"_id": notification_id},
                {
                    "$set": {
                        "is_sent": True,
                        "sent_at": datetime.utcnow()
                    },
                    "$push": {
                        "delivered_channels": channel
                    }
                }
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error marking notification sent: {str(e)}")
            return False
    
    # ==================== Analytics Operations ====================
    
    async def save_analytics_event(self, event_type: str, data: Dict[str, Any]):
        """Save analytics event"""
        try:
            event = {
                "type": event_type,
                "data": data,
                "timestamp": datetime.utcnow()
            }
            await self.analytics.insert_one(event)
        except Exception as e:
            logger.error(f"Error saving analytics event: {str(e)}")
    
    async def get_analytics_summary(self, days: int = 7) -> Dict[str, Any]:
        """Get analytics summary"""
        try:
            start_date = datetime.utcnow() - timedelta(days=days)
            
            # Total products
            total_products = await self.products.count_documents({})
            
            # Products scraped in period
            recent_products = await self.products.count_documents({
                "scraped_at": {"$gte": start_date}
            })
            
            # Extractions in period
            total_extractions = await self.extraction_results.count_documents({
                "started_at": {"$gte": start_date}
            })
            
            # Success rate
            successful_extractions = await self.extraction_results.count_documents({
                "started_at": {"$gte": start_date},
                "status": "success"
            })
            
            success_rate = (successful_extractions / total_extractions * 100) if total_extractions > 0 else 0
            
            # Average price
            pipeline = [
                {"$group": {
                    "_id": None,
                    "avg_price": {"$avg": "$current_price"},
                    "min_price": {"$min": "$current_price"},
                    "max_price": {"$max": "$current_price"}
                }}
            ]
            
            price_stats = await self.products.aggregate(pipeline).to_list(1)
            
            return {
                "total_products": total_products,
                "recent_products": recent_products,
                "total_extractions": total_extractions,
                "successful_extractions": successful_extractions,
                "success_rate": round(success_rate, 2),
                "price_stats": price_stats[0] if price_stats else {},
                "period_days": days
            }
            
        except Exception as e:
            logger.error(f"Error getting analytics summary: {str(e)}")
            return {}
    
    async def get_top_brands(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top brands by product count"""
        try:
            pipeline = [
                {"$group": {
                    "_id": "$brand",
                    "count": {"$sum": 1},
                    "avg_price": {"$avg": "$current_price"},
                    "avg_rating": {"$avg": "$reviews.average_rating"}
                }},
                {"$sort": {"count": -1}},
                {"$limit": limit}
            ]
            
            brands = await self.products.aggregate(pipeline).to_list(limit)
            
            return [
                {
                    "brand": b["_id"],
                    "count": b["count"],
                    "avg_price": round(b.get("avg_price", 0), 2),
                    "avg_rating": round(b.get("avg_rating", 0), 2)
                }
                for b in brands if b["_id"]
            ]
            
        except Exception as e:
            logger.error(f"Error getting top brands: {str(e)}")
            return []

# Global MongoDB client instance
mongodb_client = MongoDBClient()

async def get_mongodb() -> MongoDBClient:
    """Get MongoDB client instance"""
    if not mongodb_client._initialized:
        await mongodb_client.connect()
    return mongodb_client
