"""
Admin package - модульная админ панель
"""
from .main import admin_router
from .stats import stats_router
from .users import users_router
from .broadcast import broadcast_router
from .servers import servers_router
from .promo import promo_router

# Список всех админ роутеров для подключения в main.py
admin_routers = [
    admin_router,
    stats_router,
    users_router,
    broadcast_router,
    servers_router,
    promo_router
]