import jwt
from datetime import datetime, timedelta
from fastapi.security import OAuth2PasswordBearer
import secrets
from fastapi import Depends, HTTPException
from typing import List, Union
from app.database import patient_collection,doctor_collection

SECRET_KEY = "your-secret-key-here"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 600
REFRESH_TOKEN_EXPIRE_DAYS = 7

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

def create_access_token(user_data: dict) -> str:
    expires_delta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    expire = datetime.utcnow() + expires_delta
    to_encode = user_data.copy()
    to_encode.update({"exp": expire, "sub": user_data.get("ID")})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def create_refresh_token(user_data:dict) -> str:
    expires_delta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    expire = datetime.utcnow() + expires_delta
    to_encode = user_data.copy()
    to_encode.update({"exp": expire, "sub": user_data.get("ID")})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)



def decode_refresh_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="referesh_token expired")
    except jwt.PyJWTError as e:
        raise HTTPException(status_code=401, detail="Invalid token")


async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("ID")
        role: str = payload.get("role")
        if username is None or role is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        if role == 'patient':
            payload = await patient_collection.find_one({"ID": username})
        elif role == "doctor":
            payload = await doctor_collection.find_one({"ID": username})
        return dict({**payload, "role": role})
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=403, detail="Token expired")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

def role_required(role: str):
    def dependency(current_user:dict = Depends(get_current_user)):
        if role != "*" and current_user.get("role") != role:
            raise HTTPException(status_code=402, detail="Unauthorized access")
        return current_user
    return dependency