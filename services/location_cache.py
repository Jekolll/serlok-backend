# services/location_cache.py
# Simpan lokasi terbaru tiap user di memory (cepat, tidak perlu query DB)
from datetime import datetime

# { user_id: { lat, lng, accuracy, updated_at } }
_cache: dict[int, dict] = {}

def update(user_id: int, lat: float, lng: float, accuracy: float = None):
    _cache[user_id] = {
        "user_id":    user_id,
        "lat":        lat,
        "lng":        lng,
        "accuracy":   accuracy,
        "updated_at": datetime.utcnow().isoformat(),
    }

def get(user_id: int) -> dict | None:
    return _cache.get(user_id)

def get_many(user_ids: list[int]) -> list[dict]:
    return [_cache[uid] for uid in user_ids if uid in _cache]

def remove(user_id: int):
    _cache.pop(user_id, None)
