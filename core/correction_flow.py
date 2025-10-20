"""
Correction flow for extraction validation and fixes
"""
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import asyncio

from models.product import Product
from models.extraction_result import ExtractionResult, ExtractionStatus
from core.gemini_extractor import GeminiExtractor
from core.fallback_extractors import OpenAIExtractor, HuggingFaceExtractor
from utils.logger import logger
from utils.validators import (
    validate_asin,
    validate_price,
    validate_rating,
    validate_percentage
)
from config.settings import settings

class CorrectionFlow:
    """Handle extraction validation and correction"""
    
    def __init__(self):
        self.gemini = GeminiExtractor() if settings.gemini_api_key else None
        self.openai = OpenAIExtractor() if settings.openai_api_key else None
        self.huggingface = HuggingFaceExtractor() if settings.huggingface_api_key else None
        
        self.validation_rules = {
            "title": self._validate_title,
            "current_price": self._validate_price,
            "rating": self._validate_rating,
            "asin": self._validate_asin,
            "availability": self._validate_availability
        }
    
    async def validate_and_correct(self, product: Product, extraction_result: ExtractionResult) -> Tuple[Product, List[str]]:
        """
        Validate extracted data and correct if needed
        """
        logger.info(f"Starting validation for product: {product.asin}")
        
        # Perform validation
        validation_errors = self._validate_product(product)
        extraction_result.validation_errors = validation_errors
        
        if not validation_errors:
            logger.info(f"Product {product.asin} passed validation")
            return product, []
        
        # Log validation errors
        logger.warning(f"Product {product.asin} has {len(validation_errors)} validation errors")
        for error in validation_errors:
            logger.debug(f"Validation error: {error}")
        
        # Attempt correction
        extraction_result.needs_correction = True
        corrected_product = await self._correct_product(product, validation_errors, extraction_result)
        
        # Re-validate after correction
        remaining_errors = self._validate_product(corrected_product)
        
        if len(remaining_errors) < len(validation_errors):
            logger.info(f"Correction improved product data: {len(validation_errors)} -> {len(remaining_errors)} errors")
        
        return corrected_product, remaining_errors
    
    def _validate_product(self, product: Product) -> List[str]:
        """
        Validate product data
        """
        errors = []
        
        # Check required fields
        if not product.title or len(product.title) < 3:
            errors.append("Title is missing or too short")
        
        if not product.asin or not validate_asin(product.asin):
            errors.append(f"Invalid ASIN: {product.asin}")
        
        # Validate price
        is_valid, normalized_price = validate_price(product.current_price)
        if not is_valid:
            errors.append(f"Invalid current price: {product.current_price}")
        
        if product.original_price:
            is_valid, _ = validate_price(product.original_price)
            if not is_valid:
                errors.append(f"Invalid original price: {product.original_price}")
            elif product.original_price < product.current_price:
                errors.append("Original price cannot be less than current price")
        
        # Validate rating
        if product.reviews:
            is_valid, _ = validate_rating(product.reviews.average_rating)
            if not is_valid:
                errors.append(f"Invalid rating: {product.reviews.average_rating}")
            
            if product.reviews.total_reviews < 0:
                errors.append(f"Invalid review count: {product.reviews.total_reviews}")
        
        # Validate URLs
        if product.images:
            for i, img in enumerate(product.images):
                if not img.url or not img.url.startswith(("http://", "https://")):
                    errors.append(f"Invalid image URL at index {i}")
        
        # Business logic validation
        if product.status == "in_stock" and product.quantity_available == 0:
            errors.append("Product marked as in stock but quantity is 0")
        
        if product.alert_price and product.alert_price >= product.current_price:
            errors.append("Alert price should be less than current price")
        
        # Check for suspicious values
        if product.current_price > 100000:
            errors.append("Price seems unreasonably high")
        
        if product.reviews and product.reviews.average_rating == 5.0 and product.reviews.total_reviews > 10000:
            errors.append("Perfect rating with high review count seems suspicious")
        
        return errors
    
    async def _correct_product(self, product: Product, errors: List[str], extraction_result: ExtractionResult) -> Product:
        """
        Attempt to correct product data using AI
        """
        extraction_result.correction_attempts += 1
        
        # Try correction with available AI providers
        if self.gemini:
            try:
                return await self.gemini.correct_extraction(product, errors)
            except Exception as e:
                logger.error(f"Gemini correction failed: {str(e)}")
        
        if self.openai:
            try:
                return await self.openai.correct_extraction(product, errors)
            except Exception as e:
                logger.error(f"OpenAI correction failed: {str(e)}")
        
        # Manual corrections for common issues
        return self._apply_manual_corrections(product, errors)
    
    def _apply_manual_corrections(self, product: Product, errors: List[str]) -> Product:
        """
        Apply rule-based corrections for common issues
        """
        logger.info("Applying manual corrections")
        
        for error in errors:
            if "Invalid current price" in error:
                # Try to extract price from title or description
                import re
                price_match = re.search(r'\$?(\d+\.?\d*)', product.title)
                if price_match:
                    product.current_price = float(price_match.group(1))
            
            elif "Original price cannot be less than current price" in error:
                # Swap prices if they're reversed
                if product.original_price and product.original_price < product.current_price:
                    product.original_price, product.current_price = product.current_price, product.original_price
            
            elif "Invalid ASIN" in error and product.url:
                # Try to extract ASIN from URL
                import re
                asin_match = re.search(r'/dp/([A-Z0-9]{10})', product.url, re.IGNORECASE)
                if asin_match:
                    product.asin = asin_match.group(1).upper()
            
            elif "Title is missing" in error and product.description:
                # Use first part of description as title
                product.title = product.description[:100].split('.')[0]
            
            elif "Invalid rating" in error and product.reviews:
                # Clamp rating to valid range
                if product.reviews.average_rating > 5:
                    product.reviews.average_rating = 5.0
                elif product.reviews.average_rating < 0:
                    product.reviews.average_rating = 0.0
        
        return product
    
    def _validate_title(self, title: str) -> bool:
        """Validate product title"""
        if not title or len(title) < 3:
            return False
        if len(title) > 500:
            return False
        # Check for spam indicators
        spam_keywords = ["click here", "buy now", "limited time", "act now"]
        if any(keyword in title.lower() for keyword in spam_keywords):
            return False
        return True
    
    def _validate_price(self, price: Any) -> bool:
        """Validate price value"""
        is_valid, _ = validate_price(price)
        return is_valid
    
    def _validate_rating(self, rating: Any) -> bool:
        """Validate rating value"""
        is_valid, _ = validate_rating(rating)
        return is_valid
    
    def _validate_asin(self, asin: str) -> bool:
        """Validate ASIN format"""
        return validate_asin(asin)
    
    def _validate_availability(self, status: str) -> bool:
        """Validate availability status"""
        valid_statuses = ["in_stock", "out_of_stock", "limited_stock", "pre_order", "discontinued", "unknown"]
        return status in valid_statuses
    
    async def validate_batch(self, products: List[Product]) -> Dict[str, Any]:
        """
        Validate batch of products and return statistics
        """
        total = len(products)
        valid = 0
        corrected = 0
        failed = 0
        
        results = []
        
        for product in products:
            extraction_result = ExtractionResult(
                task_id=f"validate_{product.asin}",
                product_url=product.url,
                asin=product.asin
            )
            
            corrected_product, errors = await self.validate_and_correct(product, extraction_result)
            
            if not errors:
                valid += 1
            elif len(errors) < len(extraction_result.validation_errors):
                corrected += 1
            else:
                failed += 1
            
            results.append({
                "product": corrected_product,
                "errors": errors,
                "status": "valid" if not errors else "corrected" if corrected > 0 else "failed"
            })
        
        return {
            "total": total,
            "valid": valid,
            "corrected": corrected,
            "failed": failed,
            "success_rate": (valid + corrected) / total if total > 0 else 0,
            "results": results
          }
