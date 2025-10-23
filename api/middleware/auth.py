"""
Authentication middleware and utilities
"""
from fastapi import Depends, HTTPException, status, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, APIKeyHeader
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, EmailStr
import secrets
import hashlib

from config.settings import settings
from utils.logger import logger
from storage.mongodb_client import get_mongodb

# ==================== Constants ====================

API_KEY_PREFIX = "sk"
API_KEY_LENGTH = 32

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Security schemes
bearer_scheme = HTTPBearer(description="JWT Bearer Token")
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

# ==================== Models ====================

class TokenData(BaseModel):
    """Token data model"""
    username: str
    user_id: Optional[str] = None
    scopes: list[str] = Field(default_factory=list)
    token_type: str = "access"


class Token(BaseModel):
    """Token response model"""
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in: int


class User(BaseModel):
    """User model for responses"""
    id: str
    username: str
    email: EmailStr
    full_name: Optional[str] = None
    disabled: bool = False
    scopes: list[str] = Field(default_factory=list)
    created_at: datetime
    last_login: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserInDB(User):
    """User in database with hashed password"""
    hashed_password: str
    api_key: str
    last_api_usage: Optional[datetime] = None


class UserCreate(BaseModel):
    """User creation model"""
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: Optional[str] = Field(None, max_length=100)


# ==================== Password Utilities ====================

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify password against hash
    
    Args:
        plain_password: Password in plain text
        hashed_password: Hashed password from database
        
    Returns:
        True if password matches, False otherwise
    """
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        logger.error(f"Password verification error: {str(e)}")
        return False


def get_password_hash(password: str) -> str:
    """
    Hash password using bcrypt
    
    Args:
        password: Password to hash
        
    Returns:
        Hashed password
    """
    return pwd_context.hash(password)


# ==================== JWT Utilities ====================

def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create JWT access token
    
    Args:
        data: Data to encode in token
        expires_delta: Custom expiration time
        
    Returns:
        Encoded JWT token
        
    Raises:
        HTTPException: If token creation fails
    """
    try:
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(
                minutes=settings.access_token_expire_minutes
            )
        
        to_encode.update({
            "exp": expire,
            "type": "access"
        })
        
        encoded_jwt = jwt.encode(
            to_encode,
            settings.secret_key,
            algorithm=settings.jwt_algorithm
        )
        
        return encoded_jwt
        
    except Exception as e:
        logger.error(f"Error creating access token: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create token"
        )


def create_refresh_token(data: dict) -> str:
    """
    Create JWT refresh token
    
    Args:
        data: Data to encode in token
        
    Returns:
        Encoded JWT refresh token
        
    Raises:
        HTTPException: If token creation fails
    """
    try:
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + timedelta(
            days=settings.refresh_token_expire_days
        )
        
        to_encode.update({
            "exp": expire,
            "type": "refresh"
        })
        
        encoded_jwt = jwt.encode(
            to_encode,
            settings.secret_key,
            algorithm=settings.jwt_algorithm
        )
        
        return encoded_jwt
        
    except Exception as e:
        logger.error(f"Error creating refresh token: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create refresh token"
        )


def decode_token(token: str) -> Dict[str, Any]:
    """
    Decode and validate JWT token
    
    Args:
        token: Token to decode
        
    Returns:
        Decoded token payload
        
    Raises:
        HTTPException: If token is invalid or expired
    """
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.jwt_algorithm]
        )
        return payload
        
    except jwt.ExpiredSignatureError:
        logger.warning("Token expired")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"}
        )
    except JWTError as e:
        logger.error(f"JWT decode error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"}
        )


# ==================== API Key Utilities ====================

def create_api_key(username: str) -> str:
    """
    Generate unique API key for user
    
    Args:
        username: Username for API key generation
        
    Returns:
        Generated API key
    """
    random_string = secrets.token_urlsafe(API_KEY_LENGTH)
    user_hash = hashlib.sha256(username.encode()).hexdigest()[:8]
    
    return f"{API_KEY_PREFIX}_{user_hash}_{random_string}"


# ==================== User Management ====================

async def get_user_by_username(username: str) -> Optional[UserInDB]:
    """
    Get user from database by username
    
    Args:
        username: Username to search for
        
    Returns:
        User object or None if not found
    """
    try:
        mongodb = await get_mongodb()
        user_doc = await mongodb.db.users.find_one({"username": username})
        
        if user_doc:
            # Convert MongoDB ObjectId to string
            user_doc["id"] = str(user_doc.pop("_id"))
            return UserInDB(**user_doc)
        
        return None
        
    except Exception as e:
        logger.error(f"Error getting user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error"
        )


async def get_user_by_api_key(api_key: str) -> Optional[UserInDB]:
    """
    Get user from database by API key
    
    Args:
        api_key: API key to search for
        
    Returns:
        User object or None if not found
    """
    try:
        mongodb = await get_mongodb()
        user_doc = await mongodb.db.users.find_one({"api_key": api_key})
        
        if user_doc:
            user_doc["id"] = str(user_doc.pop("_id"))
            return UserInDB(**user_doc)
        
        return None
        
    except Exception as e:
        logger.error(f"Error getting user by API key: {str(e)}")
        return None


async def authenticate_user(
    username: str,
    password: str
) -> Optional[UserInDB]:
    """
    Authenticate user with username and password
    
    Args:
        username: Username
        password: Password
        
    Returns:
        Authenticated user or None
    """
    user = await get_user_by_username(username)
    
    if not user:
        return None
    
    if not verify_password(password, user.hashed_password):
        return None
    
    # Update last login
    try:
        mongodb = await get_mongodb()
        await mongodb.db.users.update_one(
            {"username": username},
            {"$set": {"last_login": datetime.now(timezone.utc)}}
        )
    except Exception as e:
        logger.error(f"Error updating last login: {str(e)}")
    
    return user


async def create_user(user_data: UserCreate) -> User:
    """
    Create new user
    
    Args:
        user_data: User creation data
        
    Returns:
        Created user
        
    Raises:
        HTTPException: If user already exists or creation fails
    """
    try:
        mongodb = await get_mongodb()
        
        # Check if user exists
        existing = await mongodb.db.users.find_one({
            "$or": [
                {"username": user_data.username.lower()},
                {"email": user_data.email.lower()}
            ]
        })
        
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Username or email already exists"
            )
        
        # Create user document
        user_doc = {
            "username": user_data.username.lower(),
            "email": user_data.email.lower(),
            "full_name": user_data.full_name,
            "hashed_password": get_password_hash(user_data.password),
            "disabled": False,
            "scopes": ["read"],
            "api_key": create_api_key(user_data.username),
            "created_at": datetime.now(timezone.utc),
            "last_login": None,
            "last_api_usage": None
        }
        
        result = await mongodb.db.users.insert_one(user_doc)
        user_doc["id"] = str(result.inserted_id)
        
        logger.info(f"User created: {user_data.username}")
        return User(**user_doc)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user"
        )


# ==================== Authentication Dependencies ====================

async def get_current_user_bearer(
    credentials: HTTPAuthorizationCredentials = Security(bearer_scheme)
) -> User:
    """
    Get current user from Bearer token
    
    Args:
        credentials: HTTP Bearer credentials
        
    Returns:
        Current user
        
    Raises:
        HTTPException: If token is invalid or user not found
    """
    token = credentials.credentials
    
    payload = decode_token(token)  # decode_token already raises HTTPException
    
    username: str = payload.get("sub")
    token_type: str = payload.get("type")
    
    if not username or token_type != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    user = await get_user_by_username(username)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    if user.disabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled"
        )
    
    return user


async def get_current_user_api_key(
    api_key: Optional[str] = Security(api_key_header)
) -> Optional[User]:
    """
    Get current user from API key
    
    Args:
        api_key: API key from header
        
    Returns:
        User if valid API key, None otherwise
        
    Raises:
        HTTPException: If API key is invalid or user is disabled
    """
    if not api_key:
        return None
    
    try:
        user = await get_user_by_api_key(api_key)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key"
            )
        
        if user.disabled:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is disabled"
            )
        
        # Update last API key usage
        mongodb = await get_mongodb()
        await mongodb.db.users.update_one(
            {"api_key": api_key},
            {"$set": {"last_api_usage": datetime.now(timezone.utc)}}
        )
        
        return user
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error validating API key: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to validate API key"
        )


async def get_current_user(
    bearer_user: Optional[User] = Depends(get_current_user_bearer),
    api_key_user: Optional[User] = Depends(get_current_user_api_key)
) -> User:
    """
    Get current user from either Bearer token or API key
    Prefer Bearer token over API key
    
    Args:
        bearer_user: User from Bearer token
        api_key_user: User from API key
        
    Returns:
        Current user
        
    Raises:
        HTTPException: If user is not authenticated
    """
    if bearer_user:
        return bearer_user
    
    if api_key_user:
        return api_key_user
    
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated"
    )


def require_scopes(required_scopes: list[str]):
    """
    Dependency to check if user has required scopes
    
    Args:
        required_scopes: List of required scopes
        
    Returns:
        Dependency function
    """
    async def scope_checker(
        current_user: User = Depends(get_current_user)
    ) -> User:
        # Admin has all scopes
        if "admin" in current_user.scopes:
            return current_user
        
        # Check required scopes
        missing_scopes = set(required_scopes) - set(current_user.scopes)
        
        if missing_scopes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required scopes: {', '.join(missing_scopes)}"
            )
        
        return current_user
    
    return scope_checker


async def get_optional_user(
    current_user: Optional[User] = Depends(get_current_user)
) -> Optional[User]:
    """
    Get user if authenticated, otherwise return None
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        User if authenticated, None otherwise
    """
    return current_user
