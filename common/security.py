import time
import jwt
from fastapi import HTTPException, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from passlib.context import CryptContext
from typing import Dict, Any
from .config import Config

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
auth_scheme = HTTPBearer(auto_error=True)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    return pwd_context.verify(plain_password, password_hash)


def create_access_token(subject: str, expires_in_seconds: int = 60 * 60 * 24) -> str:
    payload = {"sub": subject, "exp": int(time.time()) + expires_in_seconds}
    token = jwt.encode(payload, Config.JWT_SECRET, algorithm="HS256")
    return token


def verify_token(creds: HTTPAuthorizationCredentials = Depends(auth_scheme)) -> Dict[str, Any]:
    token = creds.credentials
    try:
        claims = jwt.decode(token, Config.JWT_SECRET, algorithms=["HS256"])
        claims["raw_jwt"] = token
        return claims
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")