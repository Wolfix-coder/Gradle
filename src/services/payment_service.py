from datetime import datetime
from typing import Any, Optional, Dict

from model.payments import Payments
from services.database_service import DatabaseService
from utils.logging import logger

from config import Config

database_service = DatabaseService()

class PaymentService:
    async def get_unpaid_orders(self, client_id: int, status: int) -> Optional[Dict]:
        """
        Отримання не оплачених замовлень
        
        Args:
            client_id: Any - ID клієнту (може бути str "001234" або int 123)
            status: int - статус оплати (0 - не оплачено; 1 - оплачено)
        
        Returns:
            List[Payments] - список об'єктів Payments з знайденими записами, або None якщо client_id None
        """
        db = None
        try:
            db = await database_service._get_db_connection()

            if client_id == None:
                logger.warning(f"Користувача {client_id} не знайдено.")
                return None
            
            else:
                # Отримання всіх неоплачених замовлень
                query = """
                    SELECT p.*
                    FROM payments p
                    WHERE p.client_id = ? AND p.status = ?
                """
                async with db.execute(query, (client_id, status)) as cursor:
                    rows = await cursor.fetchall()
                    return [Payments(**dict(row)) for row in rows]
                    
        except Exception as e:
            logger.error(f"Помилка отримання не оплачених замовлень: {e}")
            raise
        finally:
            if db:
                await db.close()

    async def mark_confirm_pay(self, order_id: str) -> bool:
        """Змінення статусу оплати на ОПЛАЧЕНО (1)
        
        Args:
            order_id: str - ID замовлення (наприклад 12345678)

        Returns:
            True - функція внесла зміни в БД        
        """

        try:
            async with await database_service._get_db_connection() as db:
                current_time = datetime.now().isoformat()
                query = """
                UPDATE payments SET status = ?, paid_at = ?
                WHERE ID_order = ?
                """
                cursor = await db.execute(query, (1, current_time, order_id))

                if cursor.rowcount == 0:
                    logger.warning(f"Замовлення {order_id} не знайдено в БД")
                    return False
                
                await db.commit()
                return True

        except Exception as e:
            logger.error(f"Замовлення {order_id} не позначено як оплачене: {e}")
            return False