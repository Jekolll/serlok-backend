# services/ws_manager.py
# Kelola semua koneksi WebSocket aktif
# { user_id: WebSocket }

import json
from fastapi import WebSocket
from typing import Optional

class ConnectionManager:
    def __init__(self):
        # { user_id: websocket }
        self._connections: dict[int, WebSocket] = {}

    async def connect(self, user_id: int, ws: WebSocket):
        await ws.accept()
        self._connections[user_id] = ws

    def disconnect(self, user_id: int):
        self._connections.pop(user_id, None)

    def is_online(self, user_id: int) -> bool:
        return user_id in self._connections

    def online_users(self) -> list[int]:
        return list(self._connections.keys())

    async def send(self, user_id: int, data: dict):
        ws = self._connections.get(user_id)
        if ws:
            try:
                await ws.send_text(json.dumps(data))
            except Exception:
                self.disconnect(user_id)

    async def broadcast_to(self, user_ids: list[int], data: dict):
        """Kirim pesan ke beberapa user sekaligus"""
        for uid in user_ids:
            await self.send(uid, data)


# Singleton — satu instance untuk seluruh app
manager = ConnectionManager()
