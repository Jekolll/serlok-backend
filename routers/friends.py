# routers/friends.py
from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select
from models.db import get_session, User, Friendship
from routers.auth import get_current_user
from datetime import datetime

router = APIRouter()

def _friend_data(user: User, status: str, friendship_id: int) -> dict:
    return {
        "friendship_id": friendship_id,
        "id":       user.id,
        "username": user.username,
        "email":    user.email,
        "avatar_color": user.avatar_color,
        "is_online": user.is_online,
        "share_location": user.share_location,
        "status": status,
    }

@router.get("/")
def get_friends(user_id: int = Depends(get_current_user), session: Session = Depends(get_session)):
    """Ambil semua teman yang sudah accepted"""
    friendships = session.exec(
        select(Friendship).where(
            ((Friendship.user_id == user_id) | (Friendship.friend_id == user_id)),
            Friendship.status == "accepted"
        )
    ).all()

    result = []
    for f in friendships:
        other_id = f.friend_id if f.user_id == user_id else f.user_id
        other    = session.get(User, other_id)
        if other:
            result.append(_friend_data(other, "accepted", f.id))
    return result

@router.get("/requests")
def get_requests(user_id: int = Depends(get_current_user), session: Session = Depends(get_session)):
    """Ambil permintaan pertemanan masuk"""
    reqs = session.exec(
        select(Friendship).where(
            Friendship.friend_id == user_id,
            Friendship.status    == "pending"
        )
    ).all()

    result = []
    for f in reqs:
        sender = session.get(User, f.user_id)
        if sender:
            result.append(_friend_data(sender, "pending", f.id))
    return result

@router.post("/add/{username}")
def add_friend(
    username: str,
    user_id: int = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    target = session.exec(select(User).where(User.username == username)).first()
    if not target:
        raise HTTPException(404, f"User '{username}' tidak ditemukan")
    if target.id == user_id:
        raise HTTPException(400, "Tidak bisa add diri sendiri")

    # Cek sudah berteman
    existing = session.exec(
        select(Friendship).where(
            ((Friendship.user_id == user_id) & (Friendship.friend_id == target.id)) |
            ((Friendship.user_id == target.id) & (Friendship.friend_id == user_id))
        )
    ).first()

    if existing:
        if existing.status == "accepted":
            raise HTTPException(400, "Sudah berteman")
        if existing.status == "pending":
            raise HTTPException(400, "Permintaan sudah terkirim")

    f = Friendship(user_id=user_id, friend_id=target.id, status="pending")
    session.add(f)
    session.commit()
    return {"ok": True, "msg": f"Permintaan pertemanan dikirim ke {username}"}

@router.post("/accept/{friendship_id}")
def accept_friend(
    friendship_id: int,
    user_id: int = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    f = session.get(Friendship, friendship_id)
    if not f or f.friend_id != user_id:
        raise HTTPException(404, "Permintaan tidak ditemukan")
    f.status = "accepted"
    session.add(f)
    session.commit()
    return {"ok": True, "msg": "Pertemanan diterima"}

@router.delete("/remove/{friendship_id}")
def remove_friend(
    friendship_id: int,
    user_id: int = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    f = session.get(Friendship, friendship_id)
    if not f or (f.user_id != user_id and f.friend_id != user_id):
        raise HTTPException(404, "Tidak ditemukan")
    session.delete(f)
    session.commit()
    return {"ok": True}

@router.get("/search/{query}")
def search_users(
    query: str,
    user_id: int = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    users = session.exec(
        select(User).where(
            User.username.contains(query),
            User.id != user_id
        ).limit(10)
    ).all()
    return [{"id": u.id, "username": u.username, "avatar_color": u.avatar_color} for u in users]
