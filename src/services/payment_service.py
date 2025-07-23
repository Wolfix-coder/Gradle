import aiosqlite

from datetime import datetime
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

    async def get_unpaid_orders(self, status: int, order_id: Optional[int] = None) -> Union[List[Payments], Payments, None]:
        """
        Отримання не оплачених замовлень
        
        Args:
            order_id: Якщо вказано, повертає конкретне замовлення. Якщо None - всі неоплачені замовлення
            status: int
            
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
                    SELECT p.*, o.ID_user, o.ID_worker, o.subject, o.type_work, o.order_details
                    FROM payments p
                    JOIN order o ON p.ID_order = o.ID_order
                    WHERE p.status = ? AND p.ID_order = ?
                """
                async with db.execute(query, (order_id, status)) as cursor:
                    row = await cursor.fetchone()
                    return Payments(**dict(row)) if row else None
            else:
                # Отримання всіх неоплачених замовлень
                query = """
                    SELECT p.*, o.ID_user, o.ID_worker, o.subject, o.type_work, o.order_details
                    FROM payments p
                    JOIN order o ON p.ID_order = o.ID_order
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

    async def mark_confirm_pay(self, order_id: str) -> bool:
        """Змінення статусу оплати на ОПЛАЧЕНО (1)"""

        try:
            async with await self._get_db_connection() as db:
                current_time = datetime.now().isoformat()
                query = """
                UPDATE orders SET status = ?, paid_at = ?
                WHERE order_id = ?
                """
                await db.execute(query, (1, current_time, order_id))
                await db.commit()
                return True

        except Exception as e:
            logger.error(f"Замовлення {order_id} не позначено як оплачене: {e}")
            return False