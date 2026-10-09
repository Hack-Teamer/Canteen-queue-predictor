import pytest
from app.models.order import OrderStatus


@pytest.mark.asyncio
async def test_full_canteen_order_flow(client):
    # 1. Register student
    reg_payload = {
        "name": "Alice Wonderland",
        "email": "alice@student.queuesense.edu",
        "password": "alicepassword123",
    }
    reg_res = await client.post("/api/v1/auth/register", json=reg_payload)
    assert reg_res.status_code == 201
    user_id = reg_res.json()["id"]

    # 2. Login student
    login_payload = {
        "email": "alice@student.queuesense.edu",
        "password": "alicepassword123",
    }
    login_res = await client.post("/api/v1/auth/login", json=login_payload)
    assert login_res.status_code == 200
    student_token = login_res.json()["access_token"]
    student_headers = {"Authorization": f"Bearer {student_token}"}

    # 3. Browse menu
    menu_res = await client.get("/api/v1/menu")
    assert menu_res.status_code == 200
    items = menu_res.json()
    assert len(items) >= 1
    item_id = items[0]["id"]

    # 4. Place order
    order_payload = {
        "items": [
            {"menu_item_id": item_id, "quantity": 2}
        ]
    }
    order_res = await client.post("/api/v1/orders", json=order_payload, headers=student_headers)
    assert order_res.status_code == 201
    order_data = order_res.json()
    order_id = order_data["order_id"]
    token_num = order_data["token_number"]
    assert token_num >= 1
    assert "wait" in order_data
    assert order_data["wait"]["low"] <= order_data["wait"]["median"] <= order_data["wait"]["high"]

    # 5. Check queue summary
    queue_res = await client.get("/api/v1/queue")
    assert queue_res.status_code == 200
    assert queue_res.json()["active_orders"] >= 1

    # 6. Login kitchen staff
    kitchen_login = {
        "email": "kitchen@queuesense.edu",
        "password": "kitchen123",
    }
    k_login_res = await client.post("/api/v1/auth/login", json=kitchen_login)
    assert k_login_res.status_code == 200
    kitchen_token = k_login_res.json()["access_token"]
    kitchen_headers = {"Authorization": f"Bearer {kitchen_token}"}

    # 7. Kitchen views orders
    k_orders_res = await client.get("/api/v1/kitchen/orders", headers=kitchen_headers)
    assert k_orders_res.status_code == 200
    k_orders = k_orders_res.json()
    assert any(o["order_id"] == order_id for o in k_orders)

    # 8. Kitchen accepts order
    accept_res = await client.patch(
        f"/api/v1/kitchen/orders/{order_id}/status",
        json={"status": "accepted"},
        headers=kitchen_headers,
    )
    assert accept_res.status_code == 200
    assert accept_res.json()["status"] == "accepted"

    # 9. Kitchen prepares order
    prep_res = await client.patch(
        f"/api/v1/kitchen/orders/{order_id}/status",
        json={"status": "preparing"},
        headers=kitchen_headers,
    )
    assert prep_res.status_code == 200
    assert prep_res.json()["status"] == "preparing"

    # 10. Kitchen marks order ready
    ready_res = await client.patch(
        f"/api/v1/kitchen/orders/{order_id}/status",
        json={"status": "ready"},
        headers=kitchen_headers,
    )
    assert ready_res.status_code == 200
    assert ready_res.json()["status"] == "ready"

    # 11. Student checks notifications
    notif_res = await client.get("/api/v1/notifications", headers=student_headers)
    assert notif_res.status_code == 200
    notifs = notif_res.json()
    assert len(notifs) >= 1
    assert any("ready" in n["title"].lower() for n in notifs)

    # 12. Kitchen marks order collected
    collected_res = await client.patch(
        f"/api/v1/kitchen/orders/{order_id}/status",
        json={"status": "collected"},
        headers=kitchen_headers,
    )
    assert collected_res.status_code == 200
    assert collected_res.json()["status"] == "collected"
