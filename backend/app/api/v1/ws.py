import json
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect, status

from app.core.logging import logger
from app.core.security import decode_token
from app.core.websocket_manager import ws_manager
from app.models.user import UserRole

ws_router = APIRouter()


@ws_router.websocket("/queue")
async def websocket_queue_endpoint(
    websocket: WebSocket,
    token: str = Query(...),
):
    try:
        payload = decode_token(token)
        user_id = payload.get("sub")
        if not user_id:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
    except Exception as e:
        logger.warning(f"WebSocket auth failed: {e}")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await ws_manager.connect_queue(websocket, user_id)
    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                # Handle client-side commands like subscribe to an order
                if msg.get("action") == "subscribe_order" and "order_id" in msg:
                    ws_manager.subscribe_order(msg["order_id"], websocket)
                elif msg.get("action") == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        ws_manager.disconnect_queue(websocket, user_id)


@ws_router.websocket("/kitchen")
async def websocket_kitchen_endpoint(
    websocket: WebSocket,
    token: str = Query(...),
):
    try:
        payload = decode_token(token)
        user_id = payload.get("sub")
        role = payload.get("role")
        if not user_id or role not in [UserRole.KITCHEN.value, UserRole.ADMIN.value]:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
    except Exception as e:
        logger.warning(f"Kitchen WebSocket auth failed: {e}")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await ws_manager.connect_kitchen(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                if msg.get("action") == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        ws_manager.disconnect_kitchen(websocket)
