"""
Fallback extractors for when Gemini is unavailable
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
import json
import httpx
from openai import AsyncOpenAI
from abc import ABC, abstractmethod

from config.settings import settings
from utils.logger import logger
from models.product import Product
from models.extraction_result import ExtractionResult

class BaseExtractor(ABC):
    """Base class for AI extractors"""
    
    @abstractmethod
    async def extract_product_data(self, html_content: str, extraction_result: ExtractionResult) -> Product:
        """Extract product data from HTML"""
        pass
    
    @abstractmethod
    async def correct_extraction(self, product: Product, errors: List[str]) -> Product:
        """Correct extraction errors"""
        pass

class OpenAIExtractor(BaseExtractor):
    """OpenAI GPT extractor as fallback"""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or settings.openai_api_key
        if not self.api_key:
            raise ValueError("OpenAI API key is required")
        
        self.client = AsyncOpenAI(api_key=self.api_key)
        self.model = settings.ai_model_openai
    
    async def extract_product_data(self, html_content: str, extraction_result: ExtractionResult) -> Product:
        """Extract using OpenAI GPT"""
        try:
            logger.info(f"Using OpenAI extraction for task: {extraction_result.task_id}")
            
            system_prompt = """You are an expert at extracting product information from HTML.
Extract product details and return as JSON with these fields:
title, brand, current_price, original_price, currency, rating, reviews_count,
availability, features (array), description, images (array), specifications (object),
categories (array), seller_name, is_prime (boolean), shipping_info"""
            
            user_prompt = f"Extract product information from this HTML:\n\n{html_content[:30000]}"
            
            start_time = datetime.utcnow()
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,
                max_tokens=2000,
                response_format={"type": "json_object"}
            )
            
            end_time = datetime.utcnow()
            
            # Parse response
            extracted_data = json.loads(response.choices[0].message.content)
            
            # Update extraction result
            extraction_result.ai_provider = "openai"
            extraction_result.ai_model = self.model
            extraction_result.ai_processing_time = (end_time - start_time).total_seconds()
            extraction_result.ai_tokens_used = response.usage.total_tokens
            
            # Convert to Product
            return self._create_product_from_data(extracted_data, extraction_result)
            
        except Exception as e:
            logger.error(f"OpenAI extraction failed: {str(e)}")
            raise
    
    async def correct_extraction(self, product: Product, errors: List[str]) -> Product:
        """Correct extraction using OpenAI"""
        try:
            system_prompt = "You are an expert at correcting and validating product data."
            
            user_prompt = f"""
Fix the following product data based on these errors:

Current Data:
{product.json(indent=2)}

Errors to fix:
{json.dumps(errors, indent=2)}

Return the corrected data as JSON.
"""
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            
            corrected_data = json.loads(response.choices[0].message.content)
            
            # Update product
            for key, value in corrected_data.items():
                if hasattr(product, key):
                    setattr(product, key, value)
            
            return product
            
        except Exception as e:
            logger.error(f"OpenAI correction failed: {str(e)}")
            return product
    
    def _create_product_from_data(self, data: Dict[str, Any], extraction_result: ExtractionResult) -> Product:
        """Convert extracted data to Product model"""
        # Similar to GeminiExtractor._create_product_from_data
        # Implementation details...
        pass

class HuggingFaceExtractor(BaseExtractor):
    """HuggingFace model extractor as fallback"""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or settings.huggingface_api_key
        if not self.api_key:
            raise ValueError("HuggingFace API key is required")
        
        self.api_url = "https://api-inference.huggingface.co/models/"
        self.model = "microsoft/LayoutLM-v2-base-uncased"  # Or another suitable model
    
    async def extract_product_data(self, html_content: str, extraction_result: ExtractionResult) -> Product:
        """Extract using HuggingFace models"""
        try:
            logger.info(f"Using HuggingFace extraction for task: {extraction_result.task_id}")
            
            # For HuggingFace, we might use a different approach
            # like NER for specific fields
            extracted_data = await self._extract_with_ner(html_content)
            
            extraction_result.ai_provider = "huggingface"
            extraction_result.ai_model = self.model
            
            return self._create_product_from_data(extracted_data, extraction_result)
            
        except Exception as e:
            logger.error(f"HuggingFace extraction failed: {str(e)}")
            raise
    
    async def _extract_with_ner(self, text: str) -> Dict[str, Any]:
        """Use NER model for extraction"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.api_url}{self.model}",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={"inputs": text[:1000]},  # Limit text size
                timeout=30
            )
            
            if response.status_code == 200:
                # Process NER results
                entities = response.json()
                return self._process_ner_results(entities)
            else:
                raise Exception(f"HuggingFace API error: {response.status_code}")
    
    def _process_ner_results(self, entities: List[Dict]) -> Dict[str, Any]:
        """Process NER results into structured data"""
        data = {
            "title": None,
            "brand": None,
            "current_price": None,
            "features": []
        }
        
        for entity in entities:
            label = entity.get("entity_group", "").lower()
            word = entity.get("word", "")
            
            if "product" in label or "title" in label:
                data["title"] = word
            elif "brand" in label or "organization" in label:
                data["brand"] = word
            elif "price" in label or "money" in label:
                # Extract numeric value
                import re
                price_match = re.search(r'[\d.]+', word)
                if price_match:
                    data["current_price"] = float(price_match.group())
        
        return data
    
    async def correct_extraction(self, product: Product, errors: List[str]) -> Product:
        """Basic correction for HuggingFace"""
        # HuggingFace models might not be suitable for correction
        # Return original or apply basic rules
        logger.warning("HuggingFace correction not fully implemented")
        return product
    
    def _create_product_from_data(self, data: Dict[str, Any], extraction_result: ExtractionResult) -> Product:
        """Convert extracted data to Product model"""
        # Implementation similar to other extractors
        pass

class FallbackManager:
    """Manage fallback extraction strategies"""
    
    def __init__(self):
        self.extractors = []
        
        # Initialize available extractors
        if settings.gemini_api_key:
            from core.gemini_extractor import GeminiExtractor
            self.extractors.append(("gemini", GeminiExtractor()))
        
        if settings.openai_api_key:
            self.extractors.append(("openai", OpenAIExtractor()))
        
        if settings.huggingface_api_key:
            self.extractors.append(("huggingface", HuggingFaceExtractor()))
    
    async def extract_with_fallback(self, html_content: str, extraction_result: ExtractionResult) -> Optional[Product]:
        """
        Try extraction with fallback to other providers
        """
        for name, extractor in self.extractors:
            try:
                logger.info(f"Attempting extraction with {name}")
                product = await extractor.extract_product_data(html_content, extraction_result)
                logger.info(f"Successfully extracted with {name}")
                return product
            except Exception as e:
                logger.error(f"{name} extraction failed: {str(e)}")
                continue
        
        logger.error("All extractors failed")
        return None
