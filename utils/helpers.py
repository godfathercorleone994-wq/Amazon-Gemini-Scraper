"""
Helper utilities
"""
import uuid
import hashlib
import html
import re
from typing import Optional, Any, Dict, List
from datetime import datetime, timedelta
from urllib.parse import urljoin, urlparse
import random
import string

def generate_task_id(prefix: str = "task") -> str:
    """Generate unique task ID"""
    unique_id = uuid.uuid4().hex[:8]
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    return f"{prefix}_{timestamp}_{unique_id}"

def generate_short_id(length: int = 8) -> str:
    """Generate short random ID"""
    chars = string.ascii_lowercase + string.digits
    return ''.join(random.choices(chars, k=length))

def calculate_percentage_change(old_value: float, new_value: float) -> Optional[float]:
    """Calculate percentage change between two values"""
    if old_value == 0:
        return None if new_value == 0 else float('inf')
    
    change = ((new_value - old_value) / abs(old_value)) * 100
    return round(change, 2)

def format_currency(amount: float, currency: str = "USD") -> str:
    """Format amount as currency string"""
    currency_symbols = {
        "USD": "$",
        "EUR": "€",
        "GBP": "£",
        "JPY": "¥",
        "INR": "₹",
        "BRL": "R$",
        "CAD": "C$",
        "AUD": "A$"
    }
    
    symbol = currency_symbols.get(currency, currency)
    
    # Format with thousands separator
    formatted = f"{amount:,.2f}"
    
    return f"{symbol}{formatted}"

def sanitize_html(html_content: str) -> str:
    """Remove HTML tags and clean text"""
    if not html_content:
        return ""
    
    # Unescape HTML entities
    text = html.unescape(html_content)
    
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    
    # Remove extra whitespace
    text = ' '.join(text.split())
    
    return text

def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """Truncate text to maximum length"""
    if not text or len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix

def hash_string(text: str) -> str:
    """Generate SHA256 hash of string"""
    return hashlib.sha256(text.encode()).hexdigest()

def get_domain_from_url(url: str) -> Optional[str]:
    """Extract domain from URL"""
    try:
        parsed = urlparse(url)
        return parsed.netloc
    except Exception:
        return None

def is_valid_url(url: str) -> bool:
    """Check if URL is valid"""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False

def merge_dicts(dict1: Dict, dict2: Dict) -> Dict:
    """Deep merge two dictionaries"""
    result = dict1.copy()
    
    for key, value in dict2.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_dicts(result[key], value)
        else:
            result[key] = value
    
    return result

def chunk_list(lst: List, chunk_size: int) -> List[List]:
    """Split list into chunks"""
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]

def retry_with_backoff(func, max_retries: int = 3, backoff_factor: float = 2.0):
    """Retry function with exponential backoff"""
    import time
    
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            
            wait_time = backoff_factor ** attempt
            time.sleep(wait_time)

def format_datetime(dt: datetime, format: str = "short") -> str:
    """Format datetime for display"""
    if not dt:
        return ""
    
    formats = {
        "short": "%Y-%m-%d %H:%M",
        "long": "%B %d, %Y at %I:%M %p",
        "date": "%Y-%m-%d",
        "time": "%H:%M:%S",
        "iso": "%Y-%m-%dT%H:%M:%S",
        "relative": None  # Special case
    }
    
    if format == "relative":
        return get_relative_time(dt)
    
    fmt = formats.get(format, "%Y-%m-%d %H:%M:%S")
    return dt.strftime(fmt)

def get_relative_time(dt: datetime) -> str:
    """Get relative time string (e.g., '2 hours ago')"""
    if not dt:
        return ""
    
    now = datetime.utcnow()
    diff = now - dt
    
    if diff < timedelta(minutes=1):
        return "just now"
    elif diff < timedelta(hours=1):
        minutes = int(diff.total_seconds() / 60)
        return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
    elif diff < timedelta(days=1):
        hours = int(diff.total_seconds() / 3600)
        return f"{hours} hour{'s' if hours > 1 else ''} ago"
    elif diff < timedelta(days=30):
        days = diff.days
        return f"{days} day{'s' if days > 1 else ''} ago"
    else:
        return dt.strftime("%Y-%m-%d")

def safe_get(dictionary: Dict, *keys, default=None):
    """Safely get nested dictionary value"""
    result = dictionary
    for key in keys:
        if isinstance(result, dict):
            result = result.get(key)
            if result is None:
                return default
        else:
            return default
    return result

def normalize_whitespace(text: str) -> str:
    """Normalize whitespace in text"""
    if not text:
        return ""
    
    # Replace multiple spaces with single space
    text = re.sub(r'\s+', ' ', text)
    
    # Remove leading/trailing whitespace
    return text.strip()

def extract_domain_name(url: str) -> Optional[str]:
    """Extract clean domain name from URL (without www, etc.)"""
    domain = get_domain_from_url(url)
    if not domain:
        return None
    
    # Remove www prefix
    domain = re.sub(r'^www\.', '', domain)
    
    # Extract main domain name
    parts = domain.split('.')
    if len(parts) >= 2:
        return parts[-2]
    
    return domain
