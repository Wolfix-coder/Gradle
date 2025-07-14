import aiosqlite

from typing import List, Optional, Union

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

    async def get_unpaid_orders(self, order_id: Optional[int] = None) -> Union[List[Payments], Payments, None]:
        """
        Отримання не оплачених замовлень
        
        Args:
            order_id: Якщо вказано, повертає конкретне замовлення. Якщо None - всі неоплачені замовлення
            
        Returns:
            List[Payments] якщо order_id=None
            Payments якщо order_id вказано і замовлення знайдено
            None якщо order_id вказано але замовлення не знайдено
        """
        db = None
        try:
            db = await self._get_db_connection()
            
            if order_id is not None:
                # Отримання конкретного замовлення
                query = """
                    SELECT p.*, ro.ID_worker, ro.subject, ro.type_work, ro.order_details
                    FROM payments p
                    JOIN request_order ro ON p.ID_order = ro.ID_order
                    WHERE p.status = 0 AND p.ID_order = ?
                """
                async with db.execute(query, (order_id,)) as cursor:
                    row = await cursor.fetchone()
                    return Payments(**dict(row)) if row else None
            else:
                # Отримання всіх неоплачених замовлень
                query = """
                    SELECT p.*, ro.ID_worker, ro.subject, ro.type_work, ro.order_details
                    FROM payments p
                    JOIN request_order ro ON p.ID_order = ro.ID_order
                    WHERE p.status = 0
                    ORDER BY p.created_at DESC
                """
                async with db.execute(query) as cursor:
                    rows = await cursor.fetchall()
                    return [Payments(**dict(row)) for row in rows]
                    
        except Exception as e:
            logger.error(f"Помилка отримання не оплачених замовлень: {e}")
            raise
        finally:
            if db:
                await db.close()