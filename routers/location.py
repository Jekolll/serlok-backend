# routers/location.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, Header
from sqlmodel import Session, select
from datetime import datetime
import json

from models.db import get_session, User, Friendship, GroupMember, LocationLog, engine
from services.ws_manager import manager
from services import location_cache, auth_service
from routers.auth import get_current_user

router = APIRouter()


def _get_friend_ids(user_id: int) -> list[int]:
    with Session(engine) as session:
        friendships = session.exec(
            select(Friendship).where(
                ((Friendship.user_id == user_id) | (Friendship.friend_id == user_id)),
                Friendship.status == "accepted"
            )
        ).all()
        return [
            f.friend_id if f.user_id == user_id else f.user_id
            for f in friendships
        ]


# ── WebSocket — koneksi real-time ─────────────────────────────

@router.websocket("/ws/{token}")
async def websocket_endpoint(websocket: WebSocket, token: str):
    user_id = auth_service.decode_token(token)
    if not user_id:
        await websocket.close(code=4001)
        return

    await manager.connect(user_id, websocket)

    # Update status online
    with Session(engine) as session:
        user = session.get(User, user_id)
        if user:
            user.is_online  = True
            user.last_seen  = datetime.utcnow()
            session.add(user)
            session.commit()

    # Beritahu teman-teman bahwa user online
    friend_ids = _get_friend_ids(user_id)
    await manager.broadcast_to(friend_ids, {
        "type":    "user_online",
        "user_id": user_id,
    })

    # Kirim lokasi teman-teman yang sedang online ke user ini
    friends_locs = location_cache.get_many(friend_ids)
    if friends_locs:
        await manager.send(user_id, {
            "type":      "bulk_location",
            "locations": friends_locs,
        })

    try:
        while True:
            raw = await websocket.receive_text()
            data = json.loads(raw)

            if data.get("type") == "location":
                lat = data.get("lat")
                lng = data.get("lng")
                acc = data.get("accuracy")

                if lat is None or lng is None:
                    continue

                # Update cache
                location_cache.update(user_id, lat, lng, acc)

                # Simpan ke DB setiap 10 update (tidak perlu setiap detik)
                with Session(engine) as session:
                    user = session.get(User, user_id)
                    if user:
                        user.last_seen = datetime.utcnow()
                        session.add(user)

                        # Simpan log setiap menit
                        last_log = session.exec(
                            select(LocationLog)
                            .where(LocationLog.user_id == user_id)
                            .order_by(LocationLog.recorded_at.desc())
                        ).first()

                        now = datetime.utcnow()
                        should_log = (
                            not last_log or
                            (now - last_log.recorded_at).total_seconds() >= 60
                        )
                        if should_log:
                            session.add(LocationLog(user_id=user_id, lat=lat, lng=lng, accuracy=acc))
                        session.commit()

                # Broadcast lokasi ke semua teman online
                payload = {
                    "type":    "location",
                    "user_id": user_id,
                    "lat":     lat,
                    "lng":     lng,
                    "accuracy": acc,
                }
                online_friends = [fid for fid in friend_ids if manager.is_online(fid)]
                await manager.broadcast_to(online_friends, payload)

            elif data.get("type") == "ping":
                await manager.send(user_id, {"type": "pong"})

    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(user_id)
        location_cache.remove(user_id)

        with Session(engine) as session:
            user = session.get(User, user_id)
            if user:
                user.is_online = False
                user.last_seen = datetime.utcnow()
                session.add(user)
                session.commit()

        await manager.broadcast_to(friend_ids, {
            "type":    "user_offline",
            "user_id": user_id,
        })


# ── REST — ambil lokasi & history ─────────────────────────────

@router.get("/friends")
def friends_locations(user_id: int = Depends(get_current_user)):
    """Ambil lokasi terbaru semua teman"""
    friend_ids = _get_friend_ids(user_id)
    return location_cache.get_many(friend_ids)

@router.get("/history/{target_user_id}")
def location_history(
    target_user_id: int,
    user_id: int = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Ambil riwayat perjalanan user (hanya teman sendiri)"""
    friend_ids = _get_friend_ids(user_id)
    if target_user_id != user_id and target_user_id not in friend_ids:
        raise HTTPException(403, "Bukan temanmu")

    logs = session.exec(
        select(LocationLog)
        .where(LocationLog.user_id == target_user_id)
        .order_by(LocationLog.recorded_at.desc())
        .limit(200)
    ).all()

    return [
        {"lat": l.lat, "lng": l.lng, "recorded_at": l.recorded_at.isoformat()}
        for l in logs
    ]
