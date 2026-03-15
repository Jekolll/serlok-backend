# routers/auth.py
from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel, EmailStr
from sqlmodel import Session
from models.db import get_session, User
from services import auth_service

router = APIRouter()

class RegisterBody(BaseModel):
    email:    EmailStr
    username: str
    password: str

class LoginBody(BaseModel):
    email:    EmailStr
    password: str

def get_current_user(authorization: str = Header(...)) -> int:
    token   = authorization.replace("Bearer ", "")
    user_id = auth_service.decode_token(token)
    if not user_id:
        raise HTTPException(401, "Token tidak valid")
    return user_id

def user_response(user: User) -> dict:
    return {
        "id":       user.id,
        "email":    user.email,
        "username": user.username,
        "avatar_color": user.avatar_color,
        "is_online": user.is_online,
        "share_location": user.share_location,
    }

@router.post("/register")
def register(body: RegisterBody, session: Session = Depends(get_session)):
    # Cek email & username sudah ada
    from sqlmodel import select
    if session.exec(select(User).where(User.email == body.email)).first():
        raise HTTPException(400, "Email sudah terdaftar")
    if session.exec(select(User).where(User.username == body.username)).first():
        raise HTTPException(400, "Username sudah dipakai")
    if len(body.username) < 3:
        raise HTTPException(400, "Username minimal 3 karakter")

    user  = auth_service.register(body.email, body.username, body.password, session)
    token = auth_service.make_token(user.id)
    return {"token": token, "user": user_response(user)}

@router.post("/login")
def login(body: LoginBody, session: Session = Depends(get_session)):
    user = auth_service.login(body.email, body.password, session)
    if not user:
        raise HTTPException(401, "Email atau password salah")
    token = auth_service.make_token(user.id)
    return {"token": token, "user": user_response(user)}

@router.get("/me")
def me(user_id: int = Depends(get_current_user), session: Session = Depends(get_session)):
    user = auth_service.get_user(user_id, session)
    if not user:
        raise HTTPException(404, "User tidak ditemukan")
    return user_response(user)

@router.patch("/settings")
def update_settings(
    body: dict,
    user_id: int = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(404, "User tidak ditemukan")
    if "share_location" in body:
        user.share_location = body["share_location"]
    if "username" in body and len(body["username"]) >= 3:
        user.username = body["username"]
    session.add(user)
    session.commit()
    return user_response(user)
