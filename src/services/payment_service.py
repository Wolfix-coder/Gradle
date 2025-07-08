import aiosqlite

from typing import List

from config import Config

from model.payments import Payments
from services.database import DatabaseService
from utils.logging import logger

class PaymentService:
    
    def __init__(self):
        self.db_path = Config.DATABASE_PATH

    async def _get_db_connection(self):
        """Підключення до БД"""
        try:
            db = await aiosqlite.connect(self.db_path)
            db.row_factory = aiosqlite.Row
            return db
        except Exception as e:
            logger.error(f"Error creating database connection: {e}")
            raise

    async def get_unpaid_orders(self) -> List[Payments]:
        """Отримання не оплачених замовленнь"""
        db = None
        try:
            db = await self._get_db_connection()
            query = """
                SELECT p.*, ro.subject, ro.type_work, ro.order_details
                FROM payments p
                JOIN request_order ro ON p.ID_order = ro.ID_order
                WHERE p.status = 0
                ORDER BY p.created_at DESC
            """
            async with db.execute(query) as cursor:
                rows = await cursor.fetchall()
                return [Payments(**dict(row)) for row in rows]
        except Exception as e:
            logger.error("Помилка отримання не оплачених замовлень")
            raise
        finally:
            if db:
                await db.close()