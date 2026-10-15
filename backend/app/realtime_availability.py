from collections import defaultdict
import asyncio
from fastapi import WebSocket

class AvailabilityManager:
    def __init__(self):
        self.connections = defaultdict(set)
        self.lock = asyncio.Lock()

    async def connect(self, event_id: int, websocket: WebSocket):
        await websocket.accept()
        async with self.lock:
            self.connections[event_id].add(websocket)

    async def disconnect(self, event_id: int, websocket: WebSocket):
        async with self.lock:
            clients = self.connections.get(event_id)
            if clients:
                clients.discard(websocket)
                if not clients:
                    self.connections.pop(event_id, None)

    async def broadcast(self, event_id: int, data: dict):
        async with self.lock:
            clients = list(self.connections.get(event_id, set()))
        for ws in clients:
            try:
                await ws.send_json(data)
            except Exception:
                await self.disconnect(event_id, ws)

availability_manager = AvailabilityManager()
