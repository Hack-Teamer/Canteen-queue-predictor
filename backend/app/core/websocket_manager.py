import json
from typing import Dict, List, Set
from fastapi import WebSocket
from app.core.logging import logger


class WebSocketManager:
    def __init__(self) -> None:
        # Active connections per room
        self.kitchen_sockets: Set[WebSocket] = set()
        self.queue_sockets: Set[WebSocket] = set()
        self.user_sockets: Dict[str, Set[WebSocket]] = {}
        self.order_subscriptions: Dict[str, Set[WebSocket]] = {}

    async def connect_kitchen(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.kitchen_sockets.add(websocket)
        logger.info("WebSocket connected to kitchen room")

    def disconnect_kitchen(self, websocket: WebSocket) -> None:
        self.kitchen_sockets.discard(websocket)
        logger.info("WebSocket disconnected from kitchen room")

    async def connect_queue(self, websocket: WebSocket, user_id: str) -> None:
        await websocket.accept()
        self.queue_sockets.add(websocket)
        if user_id not in self.user_sockets:
            self.user_sockets[user_id] = set()
        self.user_sockets[user_id].add(websocket)
        logger.info(f"WebSocket connected to queue room for user {user_id}")

    def disconnect_queue(self, websocket: WebSocket, user_id: str) -> None:
        self.queue_sockets.discard(websocket)
        if user_id in self.user_sockets:
            self.user_sockets[user_id].discard(websocket)
            if not self.user_sockets[user_id]:
                del self.user_sockets[user_id]
        # Clean up any order subscriptions
        for order_id, sockets in list(self.order_subscriptions.items()):
            sockets.discard(websocket)
            if not sockets:
                del self.order_subscriptions[order_id]
        logger.info(f"WebSocket disconnected from queue room for user {user_id}")

    def subscribe_order(self, order_id: str, websocket: WebSocket) -> None:
        if order_id not in self.order_subscriptions:
            self.order_subscriptions[order_id] = set()
        self.order_subscriptions[order_id].add(websocket)

    async def broadcast_kitchen(self, message: dict) -> None:
        payload = json.dumps(message)
        dead_sockets: List[WebSocket] = []
        for socket in list(self.kitchen_sockets):
            try:
                await socket.send_text(payload)
            except Exception:
                dead_sockets.append(socket)
        for dead in dead_sockets:
            self.kitchen_sockets.discard(dead)

    async def broadcast_queue(self, message: dict) -> None:
        payload = json.dumps(message)
        dead_sockets: List[WebSocket] = []
        for socket in list(self.queue_sockets):
            try:
                await socket.send_text(payload)
            except Exception:
                dead_sockets.append(socket)
        for dead in dead_sockets:
            self.queue_sockets.discard(dead)

    async def send_to_user(self, user_id: str, message: dict) -> None:
        payload = json.dumps(message)
        sockets = self.user_sockets.get(user_id, set())
        dead_sockets: List[WebSocket] = []
        for socket in list(sockets):
            try:
                await socket.send_text(payload)
            except Exception:
                dead_sockets.append(socket)
        for dead in dead_sockets:
            sockets.discard(dead)

    async def send_to_order(self, order_id: str, message: dict) -> None:
        payload = json.dumps(message)
        sockets = self.order_subscriptions.get(order_id, set())
        dead_sockets: List[WebSocket] = []
        for socket in list(sockets):
            try:
                await socket.send_text(payload)
            except Exception:
                dead_sockets.append(socket)
        for dead in dead_sockets:
            sockets.discard(dead)


ws_manager = WebSocketManager()
