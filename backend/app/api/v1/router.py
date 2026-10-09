from fastapi import APIRouter

from app.api.v1.endpoints import (
    admin,
    auth,
    forecast,
    health,
    kitchen,
    menu,
    notifications,
    orders,
    queue,
    users,
    vision,
)

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(menu.router, prefix="/menu", tags=["menu"])
api_router.include_router(orders.router, prefix="/orders", tags=["orders"])
api_router.include_router(queue.router, prefix="/queue", tags=["queue"])
api_router.include_router(kitchen.router, prefix="/kitchen", tags=["kitchen"])
api_router.include_router(forecast.router, prefix="/forecast", tags=["forecast"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
api_router.include_router(vision.router, prefix="/vision", tags=["vision"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["notifications"])
api_router.include_router(health.router, prefix="/health", tags=["health"])
