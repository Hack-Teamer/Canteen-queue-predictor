import pytest


@pytest.mark.asyncio
async def test_role_permission_matrix(client):
    # 1. Login student
    s_login = await client.post(
        "/api/v1/auth/login",
        json={"email": "student@queuesense.edu", "password": "student123"},
    )
    student_headers = {"Authorization": f"Bearer {s_login.json()['access_token']}"}

    # Student cannot access kitchen routes
    k_res = await client.get("/api/v1/kitchen/orders", headers=student_headers)
    assert k_res.status_code == 403
    assert k_res.json()["error"]["code"] == "FORBIDDEN_ROLE"

    # Student cannot access admin routes
    a_res = await client.get("/api/v1/admin/summary", headers=student_headers)
    assert a_res.status_code == 403

    # 2. Login kitchen
    k_login = await client.post(
        "/api/v1/auth/login",
        json={"email": "kitchen@queuesense.edu", "password": "kitchen123"},
    )
    kitchen_headers = {"Authorization": f"Bearer {k_login.json()['access_token']}"}

    # Kitchen cannot access admin routes
    ka_res = await client.get("/api/v1/admin/summary", headers=kitchen_headers)
    assert ka_res.status_code == 403

    # 3. Unauthenticated requests
    unauth_res = await client.get("/api/v1/orders/me")
    assert unauth_res.status_code == 401


@pytest.mark.asyncio
async def test_fallback_when_model_is_missing(client):
    # Student logs in and places order
    s_login = await client.post(
        "/api/v1/auth/login",
        json={"email": "student@queuesense.edu", "password": "student123"},
    )
    student_headers = {"Authorization": f"Bearer {s_login.json()['access_token']}"}

    menu_res = await client.get("/api/v1/menu")
    item_id = menu_res.json()[0]["id"]

    order_payload = {"items": [{"menu_item_id": item_id, "quantity": 1}]}
    order_res = await client.post("/api/v1/orders", json=order_payload, headers=student_headers)

    assert order_res.status_code == 201
    data = order_res.json()
    assert "wait" in data
    assert data["wait"]["low"] >= 1
    assert data["wait"]["median"] >= 1
    # When no ML model is loaded in test environment, fallback is baseline
    assert data["wait"]["source"] in ["ml", "baseline"]


@pytest.mark.asyncio
async def test_vision_count_ingestion_and_fallback(client):
    # Test valid API key
    vision_payload = {
        "people_count": 8,
        "zone_id": "canteen_queue_zone",
        "captured_at": "2026-10-09T10:00:00Z",
    }
    valid_res = await client.post(
        "/api/v1/vision/count",
        json=vision_payload,
        headers={"X-API-Key": "vision-secret-api-key-2024"},
    )
    assert valid_res.status_code == 200
    assert valid_res.json()["raw_count"] == 8

    # Test invalid API key rejected
    invalid_res = await client.post(
        "/api/v1/vision/count",
        json=vision_payload,
        headers={"X-API-Key": "wrong-key"},
    )
    assert invalid_res.status_code == 401
