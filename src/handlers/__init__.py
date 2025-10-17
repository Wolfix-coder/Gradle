from .admin import admin_router
from .basic import basic_router
from .comunication import comunication_router
from .orders import user_orders_router, admin_orders_router
from .payments import user_payments_router, admin_payments_router
from .statistics import statistics_router
from .users import user_router

__all__ = ['admin_router', 
           'basic_router', 
           'comunication_router',
           'user_orders_router', 
           'admin_orders_router', 
           'user_payments_router', 
           'admin_payments_router', 
           'statistics_router',
           'user_router']