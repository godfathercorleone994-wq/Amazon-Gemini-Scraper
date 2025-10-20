"""
Models for extraction results
"""
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field

class ExtractionStatus(str, Enum):
    """Status of extraction process"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FAILED = "failed"
    RETRY = "retry"

class ExtractionError(BaseModel):
    """Error details during extraction"""
    code: str
    message: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    details: Optional[Dict[str, Any]] = None

class ExtractedField(BaseModel):
    """Individual extracted field with confidence"""
    name: str
    value: Any
    confidence: float = Field(ge=0, le=1)
    source: str = "gemini"  # gemini, openai, manual
    corrected: bool = False
    original_value: Optional[Any] = None

class ExtractionResult(BaseModel):
    """Complete extraction result"""
    # Identifiers
    task_id: str
    product_url: str
    asin: Optional[str] = None
    
    # Status
    status: ExtractionStatus = ExtractionStatus.PENDING
    progress: float = Field(default=0, ge=0, le=100)
    
    # Extracted Data
    raw_html: Optional[str] = None
    extracted_fields: List[ExtractedField] = Field(default_factory=list)
    structured_data: Optional[Dict[str, Any]] = None
    
    # AI Processing
    ai_provider: str = "gemini"
    ai_model: str = "gemini-pro"
    ai_tokens_used: Optional[int] = None
    ai_processing_time: Optional[float] = None
    ai_confidence_score: Optional[float] = Field(None, ge=0, le=1)
    
    # Validation
    validation_errors: List[str] = Field(default_factory=list)
    validation_warnings: List[str] = Field(default_factory=list)
    needs_correction: bool = False
    correction_attempts: int = 0
    
    # Errors
    errors: List[ExtractionError] = Field(default_factory=list)
    
    # Timing
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    total_duration: Optional[float] = None
    
    # Metadata
    scraper_version: str = "1.0.0"
    user_agent: Optional[str] = None
    proxy_used: Optional[str] = None
    retry_count: int = 0
    
    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
    
    def add_field(self, name: str, value: Any, confidence: float = 1.0, source: str = "gemini"):
        """Add extracted field"""
        field = ExtractedField(
            name=name,
            value=value,
            confidence=confidence,
            source=source
        )
        self.extracted_fields.append(field)
    
    def get_field(self, name: str) -> Optional[ExtractedField]:
        """Get specific extracted field"""
        for field in self.extracted_fields:
            if field.name == name:
                return field
        return None
    
    def calculate_average_confidence(self) -> float:
        """Calculate average confidence across all fields"""
        if not self.extracted_fields:
            return 0.0
        
        total_confidence = sum(field.confidence for field in self.extracted_fields)
        return total_confidence / len(self.extracted_fields)
    
    def mark_completed(self):
        """Mark extraction as completed"""
        self.completed_at = datetime.utcnow()
        if self.started_at:
            delta = self.completed_at - self.started_at
            self.total_duration = delta.total_seconds()
        self.progress = 100
