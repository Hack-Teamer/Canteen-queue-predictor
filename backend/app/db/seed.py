import asyncio
import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash
from app.db.session import async_session_factory
from app.models.user import User, UserRole
from app.models.station import Station
from app.models.menu_item import MenuItem
from app.models.timetable_slot import TimetableSlot
from app.core.logging import logger


async def seed_data(session: AsyncSession) -> None:
    # 1. Seed Users
    demo_users = [
        {
            "name": "Demo Student",
            "email": "student@queuesense.edu",
            "password": "student123",
            "role": UserRole.STUDENT,
        },
        {
            "name": "Kitchen Staff",
            "email": "kitchen@queuesense.edu",
            "password": "kitchen123",
            "role": UserRole.KITCHEN,
        },
        {
            "name": "Canteen Admin",
            "email": "admin@queuesense.edu",
            "password": "admin123",
            "role": UserRole.ADMIN,
        },
    ]

    for u_data in demo_users:
        stmt = select(User).where(User.email == u_data["email"])
        result = await session.execute(stmt)
        existing = result.scalar_one_or_none()
        if not existing:
            user = User(
                name=u_data["name"],
                email=u_data["email"],
                password_hash=get_password_hash(u_data["password"]),
                role=u_data["role"],
                is_active=True,
            )
            session.add(user)

    await session.flush()

    # 2. Seed Stations
    stations_data = [
        {"name": "Tea Counter", "active_cooks": 2},
        {"name": "Tawa", "active_cooks": 2},
        {"name": "Fryer", "active_cooks": 1},
    ]

    station_map = {}
    for s_data in stations_data:
        stmt = select(Station).where(Station.name == s_data["name"])
        result = await session.execute(stmt)
        existing_station = result.scalar_one_or_none()
        if not existing_station:
            new_station = Station(
                name=s_data["name"],
                active_cooks=s_data["active_cooks"],
                is_active=True,
            )
            session.add(new_station)
            await session.flush()
            station_map[s_data["name"]] = new_station
        else:
            station_map[s_data["name"]] = existing_station

    # 3. Seed 15 Menu Items
    menu_items_data = [
        # Tea Counter (5 items)
        {"name": "Masala Chai", "price": 15.0, "prep_minutes": 1.5, "station": "Tea Counter"},
        {"name": "Ginger Tea", "price": 20.0, "prep_minutes": 1.5, "station": "Tea Counter"},
        {"name": "Filter Coffee", "price": 25.0, "prep_minutes": 2.0, "station": "Tea Counter"},
        {"name": "Lemon Tea", "price": 20.0, "prep_minutes": 1.5, "station": "Tea Counter"},
        {"name": "Cold Coffee", "price": 40.0, "prep_minutes": 3.0, "station": "Tea Counter"},
        # Tawa (5 items)
        {"name": "Masala Dosa", "price": 60.0, "prep_minutes": 4.5, "station": "Tawa"},
        {"name": "Plain Dosa", "price": 45.0, "prep_minutes": 3.5, "station": "Tawa"},
        {"name": "Onion Uttapam", "price": 55.0, "prep_minutes": 4.0, "station": "Tawa"},
        {"name": "Aloo Paratha", "price": 50.0, "prep_minutes": 5.0, "station": "Tawa"},
        {"name": "Paneer Paratha", "price": 70.0, "prep_minutes": 5.5, "station": "Tawa"},
        # Fryer (5 items)
        {"name": "Samosa (2 pcs)", "price": 30.0, "prep_minutes": 2.0, "station": "Fryer"},
        {"name": "Veg Cutlet", "price": 35.0, "prep_minutes": 3.0, "station": "Fryer"},
        {"name": "French Fries", "price": 50.0, "prep_minutes": 4.0, "station": "Fryer"},
        {"name": "Paneer Pakoda", "price": 60.0, "prep_minutes": 4.5, "station": "Fryer"},
        {"name": "Mirchi Bajji", "price": 30.0, "prep_minutes": 2.5, "station": "Fryer"},
    ]

    for item in menu_items_data:
        st = station_map.get(item["station"])
        if not st:
            continue
        stmt = select(MenuItem).where(MenuItem.name == item["name"])
        result = await session.execute(stmt)
        if not result.scalar_one_or_none():
            menu_item = MenuItem(
                name=item["name"],
                price=item["price"],
                prep_minutes=item["prep_minutes"],
                station_id=st.id,
                is_available=True,
            )
            session.add(menu_item)

    # 4. Seed Timetable slots (Mon-Fri)
    slots = [
        (datetime.time(9, 0), False, "Period 1 Start"),
        (datetime.time(10, 30), True, "Morning Tea Break"),
        (datetime.time(11, 0), False, "Period 3 Start"),
        (datetime.time(12, 30), True, "Lunch Break"),
        (datetime.time(13, 30), False, "Afternoon Classes"),
        (datetime.time(15, 0), True, "Evening Snack Break"),
    ]

    for day in range(0, 5):  # Mon-Fri
        for bell_time, is_break, label in slots:
            stmt = select(TimetableSlot).where(
                TimetableSlot.day_of_week == day,
                TimetableSlot.bell_time == bell_time,
            )
            result = await session.execute(stmt)
            if not result.scalar_one_or_none():
                session.add(
                    TimetableSlot(
                        day_of_week=day,
                        bell_time=bell_time,
                        is_break=is_break,
                        label=label,
                    )
                )

    await session.commit()
    logger.info("Database seeding completed successfully.")


async def main() -> None:
    async with async_session_factory() as session:
        await seed_data(session)


if __name__ == "__main__":
    asyncio.run(main())
