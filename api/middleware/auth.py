"""
Authentication middleware and utilities
"""
from fastapi import Depends, HTTPException, status, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, APIKeyHeader
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from pydantic import BaseModel

from config.settings import settings
from utils.logger import logger
from storage.mongodb_client import get_mongodb

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Security schemes
bearer_scheme = HTTPBearer()
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

class TokenData(BaseModel):
    """Token data model"""
    username: Optional[str] = None
    user_id: Optional[str] = None
    scopes: list = []

class User(BaseModel):
    """User model"""
    id: str
    username: str
    email: str
    full_name: Optional[str] = None
    disabled: bool = False
    api_key: Optional[str] = None
    scopes: list = []
    created_at: datetime
    last_login: Optional[datetime] = None

class UserInDB(User):
    """User in database with hashed password"""
    hashed_password: str

# ==================== Password Utilities ====================

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Hash password"""
    return pwd_context.hash(password)

# ==================== JWT Utilities ====================

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create JWT access token
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    
    to_encode.update({"exp": expire})
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.secret_key,
        algorithm=settings.jwt_algorithm
    )
    
    return encoded_jwt

def create_refresh_token(data: dict) -> str:
    """
    Create JWT refresh token
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=settings.refresh_token_expire_days)
    
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

def decode_token(token: str) -> Dict[str, Any]:
    """
    Decode and validate JWT token
    """
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.jwt_algorithm]
        )
        return payload
    except JWTError as e:
        logger.error(f"JWT decode error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"}
        )

# ==================== User Management ====================

async def get_user(username: str) -> Optional[UserInDB]:
    """Get user from database"""
    try:
        mongodb = await get_mongodb()
        user_doc = await mongodb.db.users.find_one({"username": username})
        
        if user_doc:
            return UserInDB(**user_doc)
        
        return None
    except Exception as e:
        logger.error(f"Error getting user: {str(e)}")
        return None

async def authenticate_user(username: str, password: str) -> Optional[UserInDB]:
    """Authenticate user with username and password"""
    user = await get_user(username)
    
    if not user:
        return None
    
    if not verify_password(password, user.hashed_password):
        return None
    
    # Update last login
    try:
        mongodb = await get_mongodb()
        await mongodb.db.users.update_one(
            {"username": username},
            {"$set": {"last_login": datetime.utcnow()}}
        )
    except Exception as e:
        logger.error(f"Error updating last login: {str(e)}")
    
    return user

async def create_user(
    username: str,
    email: str,
    password: str,
    full_name: Optional[str] = None,
    scopes: list = None
) -> User:
    """Create new user"""
    try:
        mongodb = await get_mongodb()
        
        # Check if user exists
        existing = await mongodb.db.users.find_one({
            "$or": [
                {"username": username},
                {"email": email}
            ]
        })
        
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User already exists"
            )
        
        # Create user
        user_data = {
            "username": username,
            "email": email,
            "full_name": full_name,
            "hashed_password": get_password_hash(password),
            "disabled": False,
            "scopes": scopes or ["read"],
            "created_at": datetime.utcnow(),
            "api_key": create_api_key(username)
        }
        
        result = await mongodb.db.users.insert_one(user_data)
        user_data["id"] = str(result.inserted_id)
        
        return User(**user_data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user"
        )

def create_api_key(username: str) -> str:
    """Generate API key for user"""
    import secrets
    import hashlib
    
    # Create unique API key
    random_string = secrets.token_urlsafe(32)
    user_hash = hashlib.sha256(username.encode()).hexdigest()[:8]
    
    return f"sk_{user_hash}_{random_string}"

# ==================== Authentication Dependencies ====================

async def get_current_user_bearer(
    credentials: HTTPAuthorizationCredentials = Security(bearer_scheme)
) -> User:
    """
    Get current user from Bearer token
    """
    token = credentials.credentials
    
    try:
        payload = decode_token(token)
        username: str = payload.get("sub")
        
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        token_data = TokenData(
            username=username,
            scopes=payload.get("scopes", [])
        )
        
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    user = await get_user(username=token_data.username)
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    if user.disabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    return user

async def get_current_user_api_key(
    api_key: Optional[str] = Security(api_key_header)
) -> Optional[User]:
    """
    Get current user from API key
    """
    if not api_key:
        return None
    
    try:
        mongodb = await get_mongodb()
        user_doc = await mongodb.db.users.find_one({"api_key": api_key})
        
        if not user_doc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key"
            )
        
        user = User(**user_doc)
        
        if user.disabled:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Inactive user"
            )
        
        # Update last API key usage
        await mongodb.db.users.update_one(
            {"api_key": api_key},
            {"$set": {"last_api_usage": datetime.utcnow()}}
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
    """
    # Prefer Bearer token over API key
    if bearer_user:
        return bearer_user
    
    if api_key_user:
        return api_key_user
    
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated"
    )

def check_scopes(required_scopes: list):
    """
    Check if user has required scopes
    """
    async def scope_checker(
        current_user: User = Depends(get_current_user)
    ) -> User:
        # Admin has all scopes
        if "admin" in current_user.scopes:
            return current_user
        
        # Check required scopes
        for scope in required_scopes:
            if scope not in current_user.scopes:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Not enough permissions. Required scope: {scope}"
                )
        
        return current_user
    
    return scope_checker

# ==================== Optional Authentication ====================

async def get_optional_user(
    bearer_user: Optional[User] = None,
    api_key: Optional[str] = Security(api_key_header)
) -> Optional[User]:
    """
    Get user if authenticated, otherwise return None
    """
    try:
        # Try Bearer token first
        if bearer_user:
            return await get_current_user_bearer(bearer_user)
    except:
        pass
    
    try:
        # Try API key
        if api_key:
            return await get_current_user_api_key(api_key)
    except:
        pass
    
    return None
