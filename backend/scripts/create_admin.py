import argparse
import asyncio
from pathlib import Path
import sys

# Ensure backend root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select
from app.core.logging import logger
from app.core.security import get_password_hash
from app.db.session import async_session_factory
from app.models.user import User, UserRole


async def create_admin(name: str, email: str, password: str):
    async with async_session_factory() as session:
        stmt = select(User).where(User.email == email)
        result = await session.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing:
            logger.info(f"User with email '{email}' already exists. Updating role to admin...")
            existing.role = UserRole.ADMIN
            existing.password_hash = get_password_hash(password)
        else:
            admin = User(
                name=name,
                email=email,
                password_hash=get_password_hash(password),
                role=UserRole.ADMIN,
                is_active=True,
            )
            session.add(admin)
            logger.info(f"Created admin user: {email}")
        await session.commit()


def main():
    parser = argparse.ArgumentParser(description="Create or promote an admin user")
    parser.add_argument("--name", type=str, default="Canteen Admin", help="Admin Name")
    parser.add_argument("--email", type=str, default="admin@queuesense.edu", help="Admin Email")
    parser.add_argument("--password", type=str, default="admin123", help="Admin Password")
    args = parser.parse_args()

    asyncio.run(create_admin(args.name, args.email, args.password))


if __name__ == "__main__":
    main()
