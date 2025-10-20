"""
Gemini AI extractor for structured data extraction
"""
import json
import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime
import google.generativeai as genai
from tenacity import retry, stop_after_attempt, wait_exponential

from config.settings import settings
from utils.logger import logger
from models.extraction_result import ExtractionResult, ExtractionStatus, ExtractedField
from models.product import Product, ProductStatus, PriceHistory, ProductReview

class GeminiExtractor:
    """Extract structured data using Google's Gemini AI"""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or settings.gemini_api_key
        if not self.api_key:
            raise ValueError("Gemini API key is required")
        
        # Configure Gemini
        genai.configure(api_key=self.api_key)
        
        # Initialize model
        self.model = genai.GenerativeModel(
            model_name=settings.ai_model_gemini,
            generation_config={
                "temperature": 0.1,  # Low temperature for consistent extraction
                "top_p": 0.8,
                "top_k": 40,
                "max_output_tokens": 4096,
            },
            safety_settings=[
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
            ]
        )
        
        # Load prompts
        self.extraction_prompt = self._load_prompt("extraction_prompt.txt")
        self.correction_prompt = self._load_prompt("correction_prompt.txt")
    
    def _load_prompt(self, filename: str) -> str:
        """Load prompt from file"""
        try:
            with open(f"prompts/{filename}", "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            logger.warning(f"Prompt file not found: {filename}, using default")
            return self._get_default_prompt(filename)
    
    def _get_default_prompt(self, filename: str) -> str:
        """Get default prompt if file not found"""
        if filename == "extraction_prompt.txt":
            return """
You are an expert at extracting product information from Amazon HTML pages.
Extract the following information and return it as valid JSON:

{
    "title": "Product title",
    "brand": "Brand name",
    "current_price": 0.00,
    "original_price": 0.00,
    "currency": "USD",
    "rating": 0.0,
    "reviews_count": 0,
    "availability": "in_stock|out_of_stock|limited_stock",
    "features": ["feature1", "feature2"],
    "description": "Product description",
    "images": ["url1", "url2"],
    "specifications": {"key": "value"},
    "categories": ["category1", "category2"],
    "seller_name": "Seller name",
    "is_prime": true/false,
    "shipping_info": "Shipping details"
}

HTML Content:
{html_content}

Important:
- Extract exact values from the HTML
- Use null for missing values
- Ensure valid JSON format
- Extract prices as numbers (remove currency symbols)
- Rating should be between 0-5
"""
        elif filename == "correction_prompt.txt":
            return """
Review and correct the following extracted product data.
Fix any inconsistencies, validate data types, and ensure accuracy.

Current Data:
{current_data}

Validation Errors:
{errors}

Return the corrected data as valid JSON, fixing all identified issues.
"""
        return ""
    
    @retry(
        stop=stop_after_attempt(settings.ai_max_retries),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def extract_product_data(self, html_content: str, extraction_result: ExtractionResult) -> Product:
        """
        Extract product data from HTML using Gemini
        """
        try:
            logger.info(f"Starting Gemini extraction for task: {extraction_result.task_id}")
            
            # Prepare prompt
            prompt = self.extraction_prompt.format(
                html_content=html_content[:50000]  # Limit HTML size
            )
            
            # Generate response
            start_time = datetime.utcnow()
            response = await self._generate_async(prompt)
            end_time = datetime.utcnow()
            
            # Parse response
            extracted_data = self._parse_json_response(response.text)
            
            # Update extraction result
            extraction_result.ai_processing_time = (end_time - start_time).total_seconds()
            extraction_result.ai_tokens_used = response.usage_metadata.total_token_count if hasattr(response, 'usage_metadata') else None
            
            # Convert to Product model
            product = self._create_product_from_data(extracted_data, extraction_result)
            
            # Add extracted fields to result
            for key, value in extracted_data.items():
                extraction_result.add_field(
                    name=key,
                    value=value,
                    confidence=0.9,  # High confidence for Gemini
                    source="gemini"
                )
            
            # Calculate confidence score
            extraction_result.ai_confidence_score = self._calculate_confidence(extracted_data)
            
            logger.info(f"Gemini extraction completed for task: {extraction_result.task_id}")
            
            return product
            
        except Exception as e:
            logger.error(f"Gemini extraction failed: {str(e)}")
            extraction_result.status = ExtractionStatus.FAILED
            extraction_result.errors.append({
                "code": "GEMINI_ERROR",
                "message": str(e),
                "timestamp": datetime.utcnow()
            })
            raise
    
    async def _generate_async(self, prompt: str):
        """Generate response asynchronously"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self.model.generate_content,
            prompt
        )
    
    def _parse_json_response(self, response_text: str) -> Dict[str, Any]:
        """Parse JSON from AI response"""
        try:
            # Try to extract JSON from response
            import re
            
            # Look for JSON block
            json_match = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # Try to find JSON object
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                else:
                    json_str = response_text
            
            # Parse JSON
            return json.loads(json_str)
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.debug(f"Response text: {response_text}")
            
            # Return minimal valid structure
            return {
                "title": None,
                "current_price": None,
                "availability": "unknown"
            }
    
    def _create_product_from_data(self, data: Dict[str, Any], extraction_result: ExtractionResult) -> Product:
        """Create Product model from extracted data"""
        # Map availability status
        availability_map = {
            "in_stock": ProductStatus.IN_STOCK,
            "out_of_stock": ProductStatus.OUT_OF_STOCK,
            "limited_stock": ProductStatus.LIMITED_STOCK,
            "pre_order": ProductStatus.PRE_ORDER,
            "discontinued": ProductStatus.DISCONTINUED
        }
        
        # Clean and validate price
        current_price = data.get("current_price", 0)
        if isinstance(current_price, str):
            current_price = float(re.sub(r'[^\d.]', '', current_price))
        
        original_price = data.get("original_price", current_price)
        if isinstance(original_price, str):
            original_price = float(re.sub(r'[^\d.]', '', original_price))
        
        # Create product
        product = Product(
            asin=extraction_result.asin or "UNKNOWN",
            url=extraction_result.product_url,
            title=data.get("title", "Unknown Product"),
            brand=data.get("brand"),
            current_price=current_price,
            original_price=original_price if original_price > current_price else None,
            currency=data.get("currency", "USD"),
            status=availability_map.get(data.get("availability", "unknown"), ProductStatus.UNKNOWN),
            features=data.get("features", []),
            description=data.get("description"),
            specifications=data.get("specifications", {}),
            category=data.get("categories", []),
            seller_name=data.get("seller_name"),
            ai_summary=f"Extracted by Gemini AI on {datetime.utcnow().strftime('%Y-%m-%d')}"
        )
        
        # Add price history
        if current_price > 0:
            product.price_history.append(
                PriceHistory(
                    price=current_price,
                    currency=product.currency,
                    is_discounted=original_price > current_price if original_price else False,
                    discount_percentage=product.calculate_discount()
                )
            )
        
        # Add review data if available
        if data.get("rating") or data.get("reviews_count"):
            product.reviews = ProductReview(
                average_rating=float(data.get("rating", 0)),
                total_reviews=int(data.get("reviews_count", 0))
            )
        
        # Add images
        images = data.get("images", [])
        for i, img_url in enumerate(images[:10]):  # Limit to 10 images
            product.images.append({
                "url": img_url,
                "is_primary": i == 0
            })
        
        # Add shipping info
        product.shipping = {
            "is_prime": data.get("is_prime", False),
            "free_shipping": "free" in str(data.get("shipping_info", "")).lower(),
            "shipping_info": data.get("shipping_info")
        }
        
        return product
    
    def _calculate_confidence(self, data: Dict[str, Any]) -> float:
        """Calculate confidence score based on extracted data completeness"""
        required_fields = ["title", "current_price", "availability"]
        important_fields = ["brand", "rating", "reviews_count", "features", "images"]
        
        score = 0
        total = len(required_fields) + len(important_fields) * 0.5
        
        # Check required fields
        for field in required_fields:
            if data.get(field) is not None:
                score += 1
        
        # Check important fields
        for field in important_fields:
            if data.get(field) is not None:
                score += 0.5
        
        return min(score / total, 1.0)
    
    async def correct_extraction(self, product: Product, errors: List[str]) -> Product:
        """
        Use Gemini to correct extraction errors
        """
        try:
            logger.info(f"Correcting extraction for product: {product.asin}")
            
            # Prepare correction prompt
            prompt = self.correction_prompt.format(
                current_data=product.json(indent=2),
                errors="\n".join(errors)
            )
            
            # Generate correction
            response = await self._generate_async(prompt)
            
            # Parse corrected data
            corrected_data = self._parse_json_response(response.text)
            
            # Update product with corrected data
            for key, value in corrected_data.items():
                if hasattr(product, key) and value is not None:
                    setattr(product, key, value)
            
            logger.info(f"Correction completed for product: {product.asin}")
            
            return product
            
        except Exception as e:
            logger.error(f"Correction failed: {str(e)}")
            return product  # Return original if correction fails
    
    async def analyze_reviews_sentiment(self, reviews: List[str]) -> Dict[str, Any]:
        """
        Analyze sentiment of product reviews
        """
        if not reviews:
            return {"sentiment": "neutral", "score": 0.0, "summary": "No reviews available"}
        
        prompt = f"""
Analyze the sentiment of these product reviews and provide:
1. Overall sentiment (positive/negative/neutral/mixed)
2. Sentiment score (-1 to 1)
3. Brief summary of main points
4. Common pros and cons

Reviews:
{json.dumps(reviews[:20], indent=2)}  # Limit to 20 reviews

Return as JSON:
{{
    "sentiment": "positive|negative|neutral|mixed",
    "score": 0.0,
    "summary": "Brief summary",
    "pros": ["pro1", "pro2"],
    "cons": ["con1", "con2"],
    "key_themes": ["theme1", "theme2"]
}}
"""
        
        try:
            response = await self._generate_async(prompt)
            return self._parse_json_response(response.text)
        except Exception as e:
            logger.error(f"Sentiment analysis failed: {str(e)}")
            return {"sentiment": "unknown", "score": 0.0, "summary": "Analysis failed"}
    
    async def generate_product_summary(self, product: Product) -> str:
        """
        Generate AI summary for product
        """
        prompt = f"""
Create a concise, informative summary (2-3 sentences) for this product:

Title: {product.title}
Brand: {product.brand}
Price: ${product.current_price}
Rating: {product.reviews.average_rating if product.reviews else 'N/A'}/5
Features: {', '.join(product.features[:5]) if product.features else 'N/A'}

Focus on key selling points and value proposition.
"""
        
        try:
            response = await self._generate_async(prompt)
            return response.text.strip()
        except Exception as e:
            logger.error(f"Summary generation failed: {str(e)}")
            return f"{product.title} by {product.brand}"
