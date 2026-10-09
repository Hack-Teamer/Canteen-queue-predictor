from datetime import datetime, timedelta, timezone
import pytest
from app.models.crowd_snapshot import CrowdSnapshot
from app.services.fusion_service import FusionService


@pytest.mark.asyncio
async def test_walk_ins_never_negative(db_session, fake_redis):
    fusion_service = FusionService(db_session, fake_redis)

    # Put a crowd count of 2 in Redis
    await fake_redis.set("crowd:latest", "2")

    # Suppose there are active orders in line
    res = await fusion_service.compute_fusion()
    # If online orders exceed camera count, walk-ins should be at least 0
    assert res["estimated_walk_ins"] >= 0


@pytest.mark.asyncio
async def test_stale_camera_ignored(db_session, fake_redis):
    fusion_service = FusionService(db_session, fake_redis)

    # Insert a stale crowd snapshot into DB (45 seconds ago)
    stale_time = datetime.now(timezone.utc) - timedelta(seconds=45)
    stale_snap = CrowdSnapshot(
        people_count=15,
        zone_id="canteen_queue_zone",
        captured_at=stale_time,
    )
    db_session.add(stale_snap)
    await db_session.commit()

    # Ensure Redis has no fresh key
    await fake_redis.delete("crowd:latest")

    count = await fusion_service.get_camera_count()
    assert count is None

    res = await fusion_service.compute_fusion()
    assert res["camera_available"] is False
    assert res["estimated_walk_ins"] == 0


@pytest.mark.asyncio
async def test_fresh_camera_detected(db_session, fake_redis):
    fusion_service = FusionService(db_session, fake_redis)

    # Insert a fresh crowd snapshot into DB (10 seconds ago)
    fresh_time = datetime.now(timezone.utc) - timedelta(seconds=10)
    fresh_snap = CrowdSnapshot(
        people_count=12,
        zone_id="canteen_queue_zone",
        captured_at=fresh_time,
    )
    db_session.add(fresh_snap)
    await db_session.commit()

    # Ensure Redis has no key so it reads DB
    await fake_redis.delete("crowd:latest")

    count = await fusion_service.get_camera_count()
    assert count == 12.0

    res = await fusion_service.compute_fusion()
    assert res["camera_available"] is True
    assert res["people_in_line"] == 12
