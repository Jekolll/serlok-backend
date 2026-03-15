# services/auth_service.py
import os, random, bcrypt
from datetime import datetime, timedelta
from typing import Optional
from jose import jwt, JWTError
from sqlmodel import Session, select
from models.db import User

SECRET = os.getenv("SECRET_KEY", "serlok_secret_2025")
ALG    = "HS256"
TTL    = 60 * 24 * 30

def hash_pw(plain: str) -> str:
    return bcrypt.hashpw(plain[:72].encode(), bcrypt.gensalt()).decode()

def verify_pw(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain[:72].encode(), hashed.encode())

def make_token(user_id: int) -> str:
    exp = datetime.utcnow() + timedelta(minutes=TTL)
    return jwt.encode({"sub": str(user_id), "exp": exp}, SECRET, algorithm=ALG)

def decode_token(token: str) -> Optional[int]:
    try:
        payload = jwt.decode(token, SECRET, algorithms=[ALG])
        return int(payload["sub"])
    except JWTError:
        return None

def register(email: str, username: str, password: str, session: Session) -> User:
    colors = ["#10b981","#3b82f6","#f59e0b","#ef4444","#8b5cf6","#ec4899","#06b6d4"]
    user   = User(
        email         = email,
        username      = username,
        password_hash = hash_pw(password),
        avatar_color  = random.choice(colors),
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user

def login(email: str, password: str, session: Session) -> Optional[User]:
    user = session.exec(select(User).where(User.email == email)).first()
    if not user or not verify_pw(password, user.password_hash):
        return None
    return user

def get_user(user_id: int, session: Session) -> Optional[User]:
    return session.get(User, user_id)
