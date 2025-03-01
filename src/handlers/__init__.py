from .admin import admin_router
from .orders import users_orders_router, admin_orders_router
from .payments import *
from .statistics import *

__all__ = ['admin_router', 'users_orders_router', 'admin_orders_router']