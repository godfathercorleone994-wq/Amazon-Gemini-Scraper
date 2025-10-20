"""
Validation utilities
"""
import re
from typing import Optional, List
from urllib.parse import urlparse
from email_validator import validate_email as _validate_email, EmailNotValidError

def validate_asin(asin: str) -> bool:
    """
    Validate Amazon ASIN format
    ASIN is a 10-character alphanumeric code
    """
    if not asin:
        return False
    
    pattern = r'^[A-Z0-9]{10}$'
    return bool(re.match(pattern, asin.upper()))

def validate_amazon_url(url: str) -> tuple[bool, Optional[str]]:
    """
    Validate Amazon product URL and extract ASIN
    Returns: (is_valid, asin)
    """
    if not url:
        return False, None
    
    try:
        parsed = urlparse(url)
        
        # Check if it's an Amazon domain
        amazon_domains = [
            'amazon.com', 'amazon.co.uk', 'amazon.de', 'amazon.fr',
            'amazon.es', 'amazon.it', 'amazon.ca', 'amazon.com.br',
            'amazon.in', 'amazon.com.mx', 'amazon.co.jp', 'amazon.com.au'
        ]
        
        domain_valid = any(domain in parsed.netloc for domain in amazon_domains)
        if not domain_valid:
            return False, None
        
        # Extract ASIN from URL patterns
        # Pattern 1: /dp/ASIN
        dp_match = re.search(r'/dp/([A-Z0-9]{10})', url, re.IGNORECASE)
        if dp_match:
            return True, dp_match.group(1).upper()
        
        # Pattern 2: /gp/product/ASIN
        gp_match = re.search(r'/gp/product/([A-Z0-9]{10})', url, re.IGNORECASE)
        if gp_match:
            return True, gp_match.group(1).upper()
        
        # Pattern 3: /product/ASIN
        product_match = re.search(r'/product/([A-Z0-9]{10})', url, re.IGNORECASE)
        if product_match:
            return True, product_match.group(1).upper()
        
        # Pattern 4: ASIN in query parameter
        query_match = re.search(r'[?&]ASIN=([A-Z0-9]{10})', url, re.IGNORECASE)
        if query_match:
            return True, query_match.group(1).upper()
        
        return False, None
        
    except Exception:
        return False, None

def validate_email(email: str) -> tuple[bool, Optional[str]]:
    """
    Validate email address
    Returns: (is_valid, normalized_email)
    """
    try:
        validation = _validate_email(email, check_deliverability=False)
        return True, validation.email
    except EmailNotValidError:
        return False, None

def validate_price(price: any) -> tuple[bool, Optional[float]]:
    """
    Validate and normalize price
    Returns: (is_valid, normalized_price)
    """
    if price is None:
        return False, None
    
    try:
        # Handle string prices with currency symbols
        if isinstance(price, str):
            # Remove currency symbols and spaces
            price_str = re.sub(r'[^\d.,]', '', price)
            # Replace comma with dot for decimal
            price_str = price_str.replace(',', '.')
            price_float = float(price_str)
        else:
            price_float = float(price)
        
        # Check if price is reasonable (0 to 1 million)
        if 0 <= price_float <= 1_000_000:
            return True, round(price_float, 2)
        
        return False, None
        
    except (ValueError, TypeError):
        return False, None

def validate_percentage(value: any, min_val: float = 0, max_val: float = 100) -> tuple[bool, Optional[float]]:
    """
    Validate percentage value
    Returns: (is_valid, normalized_percentage)
    """
    try:
        percentage = float(value)
        if min_val <= percentage <= max_val:
            return True, round(percentage, 2)
        return False, None
    except (ValueError, TypeError):
        return False, None

def validate_rating(rating: any) -> tuple[bool, Optional[float]]:
    """
    Validate product rating (0-5 stars)
    Returns: (is_valid, normalized_rating)
    """
    try:
        rating_float = float(rating)
        if 0 <= rating_float <= 5:
            return True, round(rating_float, 1)
        return False, None
    except (ValueError, TypeError):
        return False, None

def validate_proxy(proxy: str) -> bool:
    """
    Validate proxy format (host:port or user:pass@host:port)
    """
    if not proxy:
        return False
    
    # Pattern for proxy with auth
    auth_pattern = r'^[^:]+:[^@]+@[^:]+:\d+$'
    # Pattern for proxy without auth
    simple_pattern = r'^[^:]+:\d+$'
    
    return bool(re.match(auth_pattern, proxy) or re.match(simple_pattern, proxy))

def sanitize_string(text: str, max_length: int = 500) -> str:
    """
    Sanitize string for storage
    """
    if not text:
        return ""
    
    # Remove excess whitespace
    text = ' '.join(text.split())
    
    # Truncate if too long
    if len(text) > max_length:
        text = text[:max_length-3] + "..."
    
    return text

def extract_numbers(text: str) -> List[float]:
    """
    Extract all numbers from text
    """
    if not text:
        return []
    
    # Find all numbers (including decimals)
    numbers = re.findall(r'-?\d+\.?\d*', text)
    return [float(n) for n in numbers]
