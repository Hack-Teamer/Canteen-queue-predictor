import json
from unittest.mock import AsyncMock
import pytest
from app.core.websocket_manager import WebSocketManager


@pytest.mark.asyncio
async def test_websocket_manager_isolation_and_broadcast():
    manager = WebSocketManager()

    # Create mock WebSockets
    student1_ws = AsyncMock()
    student2_ws = AsyncMock()
    kitchen_ws = AsyncMock()

    # Connect sockets
    await manager.connect_queue(student1_ws, user_id="user-1")
    await manager.connect_queue(student2_ws, user_id="user-2")
    await manager.connect_kitchen(kitchen_ws)

    # 1. Send targeted message to student 1 only
    msg_student1 = {"type": "order_ready", "order_id": "ord-123", "token_number": 42}
    await manager.send_to_user("user-1", msg_student1)

    student1_ws.send_text.assert_called_once_with(json.dumps(msg_student1))
    student2_ws.send_text.assert_not_called()
    kitchen_ws.send_text.assert_not_called()

    # Reset mocks
    student1_ws.reset_mock()
    student2_ws.reset_mock()
    kitchen_ws.reset_mock()

    # 2. Broadcast to kitchen
    msg_kitchen = {"type": "order_updated", "order_id": "ord-123", "status": "preparing"}
    await manager.broadcast_kitchen(msg_kitchen)

    kitchen_ws.send_text.assert_called_once_with(json.dumps(msg_kitchen))
    student1_ws.send_text.assert_not_called()
    student2_ws.send_text.assert_not_called()

    # Reset mocks
    student1_ws.reset_mock()
    student2_ws.reset_mock()
    kitchen_ws.reset_mock()

    # 3. Broadcast to all queue clients
    msg_queue = {"type": "queue_summary", "active_orders": 5}
    await manager.broadcast_queue(msg_queue)

    student1_ws.send_text.assert_called_once_with(json.dumps(msg_queue))
    student2_ws.send_text.assert_called_once_with(json.dumps(msg_queue))
    kitchen_ws.send_text.assert_not_called()

    # Disconnects
    manager.disconnect_queue(student1_ws, "user-1")
    manager.disconnect_queue(student2_ws, "user-2")
    manager.disconnect_kitchen(kitchen_ws)
    assert len(manager.kitchen_sockets) == 0
    assert len(manager.queue_sockets) == 0
