# routers/groups.py
import secrets
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlmodel import Session, select
from models.db import get_session, User, Group, GroupMember
from routers.auth import get_current_user

router = APIRouter()

class CreateGroupBody(BaseModel):
    name: str

@router.post("/")
def create_group(
    body: CreateGroupBody,
    user_id: int = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    code  = secrets.token_urlsafe(6).upper()
    group = Group(name=body.name, owner_id=user_id, invite_code=code)
    session.add(group)
    session.commit()
    session.refresh(group)

    # Owner otomatis jadi member
    session.add(GroupMember(group_id=group.id, user_id=user_id))
    session.commit()

    return {"id": group.id, "name": group.name, "invite_code": group.invite_code}

@router.get("/")
def my_groups(user_id: int = Depends(get_current_user), session: Session = Depends(get_session)):
    members = session.exec(select(GroupMember).where(GroupMember.user_id == user_id)).all()
    result  = []
    for m in members:
        g = session.get(Group, m.group_id)
        if g:
            # Hitung jumlah member
            count = len(session.exec(select(GroupMember).where(GroupMember.group_id == g.id)).all())
            result.append({
                "id":          g.id,
                "name":        g.name,
                "invite_code": g.invite_code,
                "is_owner":    g.owner_id == user_id,
                "member_count": count,
            })
    return result

@router.post("/join/{code}")
def join_group(
    code: str,
    user_id: int = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    group = session.exec(select(Group).where(Group.invite_code == code.upper())).first()
    if not group:
        raise HTTPException(404, "Kode grup tidak valid")

    existing = session.exec(
        select(GroupMember).where(
            GroupMember.group_id == group.id,
            GroupMember.user_id  == user_id
        )
    ).first()
    if existing:
        raise HTTPException(400, "Sudah bergabung di grup ini")

    session.add(GroupMember(group_id=group.id, user_id=user_id))
    session.commit()
    return {"ok": True, "group": group.name}

@router.get("/{group_id}/members")
def group_members(
    group_id: int,
    user_id: int = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    # Cek user adalah member
    is_member = session.exec(
        select(GroupMember).where(
            GroupMember.group_id == group_id,
            GroupMember.user_id  == user_id
        )
    ).first()
    if not is_member:
        raise HTTPException(403, "Kamu bukan member grup ini")

    members = session.exec(select(GroupMember).where(GroupMember.group_id == group_id)).all()
    result  = []
    for m in members:
        u = session.get(User, m.user_id)
        if u:
            result.append({
                "id":       u.id,
                "username": u.username,
                "avatar_color": u.avatar_color,
                "is_online": u.is_online,
                "share_location": u.share_location,
            })
    return result

@router.delete("/{group_id}/leave")
def leave_group(
    group_id: int,
    user_id: int = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    m = session.exec(
        select(GroupMember).where(
            GroupMember.group_id == group_id,
            GroupMember.user_id  == user_id
        )
    ).first()
    if not m:
        raise HTTPException(404, "Kamu bukan member grup ini")
    session.delete(m)
    session.commit()
    return {"ok": True}
