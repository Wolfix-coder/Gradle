from typing import List, Optional, Dict, Any
from datetime import datetime
import aiosqlite
import traceback
from aiogram import Bot
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import Config
from model.order import Order, OrderStatus
from utils.logging import logger

class OrderService:
    """Service class for managing orders in the database."""
    
    def __init__(self):
        self.db_path = Config.DATABASE_PATH

    async def _get_db_connection(self):
        try:
            db = await aiosqlite.connect(self.db_path)
            db.row_factory = aiosqlite.Row
            return db
        except Exception as e:
            logger.error(f"Error creating database connection: {e}")
            raise


    async def get_new_orders(self) -> List[Order]:
        """Retrieves all new orders with associated user information."""
        db = None
        try:
            db = await self._get_db_connection()
            query = """
                SELECT ro.*, u.user_name, u.user_link
                FROM request_order ro
                JOIN users u ON ro.ID_user = u.ID
                WHERE ro.status = ?
                ORDER BY ro.created_at DESC
            """
            async with db.execute(query, (OrderStatus.NEW.value,)) as cursor:
                rows = await cursor.fetchall()
                return [Order(**dict(row)) for row in rows]
        except Exception as e:
            logger.error(f"Error getting new orders: {e}")
            raise
        finally:
            if db:
                await db.close()

    async def get_order(self, order_id: str) -> Order:
        """Retrieves a specific order by ID with user information."""
        db = None
        try:
            db = await self._get_db_connection()
            query = """
                SELECT ro.*, u.user_name, u.user_link
                FROM request_order ro
                JOIN users u ON ro.ID_user = u.ID
                WHERE ro.ID_order = ?
            """
            async with db.execute(query, (order_id,)) as cursor:
                if row := await cursor.fetchone():
                    return Order(**dict(row))
                return None
        except Exception as e:
            logger.error(f"Error getting order {order_id}: {e}")
            raise
        finally:
            if db:
                await db.close()

    async def create_order(self, order_data: Dict[str, Any]) -> Optional[str]:
        """Creates a new order and returns its ID."""
        db = None
        try:
            db = await self._get_db_connection()
            
            # Generate unique order ID
            async with db.execute("SELECT MAX(ID_order) FROM request_order") as cursor:
                last_id = await cursor.fetchone()
                new_id = f"{(int(last_id[0] or 0) + 1):06d}"

            query = """
                INSERT INTO request_order (
                    ID_order, ID_user, subject, type_work,
                    order_details, status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """
            await db.execute(query, (
                new_id,
                order_data["ID_user"],
                order_data["subject"],
                order_data["type_work"],
                order_data["order_details"],
                1,
                datetime.now().isoformat()
            ))
            await db.commit()
            return new_id
        except Exception as e:
            logger.error(f"Error creating order: {e}")
            return None
        finally:
            if db:
                await db.close()

    async def update_order_status_debug(self, order_id: str, worker_id: int, status: OrderStatus) -> bool:
        """
        Розширена версія update_order_status з додатковим логуванням для діагностики.
        
        Args:
            order_id: Order identifier
            worker_id: ID of the worker taking the order
            status: New status to set
            
        Returns:
            bool: True if order was successfully updated, False otherwise
        """
        db = None
        try:
            logger.info(f"Starting update_order_status for order {order_id}, worker {worker_id}, status {status.name}")
            
            db = await self._get_db_connection()
            logger.info(f"Database connection established: {self.db_path}")
            
            # Перевіряємо, чи існує замовлення
            check_query = "SELECT ID_order, status FROM request_order WHERE ID_order = ?"
            logger.info(f"Executing query: {check_query} with params: ({order_id},)")
            
            async with db.execute(check_query, (order_id,)) as cursor:
                row = await cursor.fetchone()
                if not row:
                    logger.error(f"Order {order_id} not found in database")
                    return False
                
                logger.info(f"Order found: {dict(row)}")
                current_status = row['status']
                
                if current_status != OrderStatus.NEW.value:
                    logger.info(f"Order {order_id} has status {current_status}, expected {OrderStatus.NEW.value}")
                    return False

            # Оновлюємо статус замовлення
            current_time = datetime.now().isoformat()
            logger.info(f"Current time for update: {current_time}")
            
            update_query = """
                UPDATE request_order 
                SET ID_worker = ?,
                    status = ?,
                    taken_at = ?,
                WHERE ID_order = ?
                AND status = ?
            """
            
            logger.info(f"Executing update query with params: ({worker_id}, {status.value}, {current_time}, {current_time}, {order_id}, {OrderStatus.NEW.value})")
            
            cursor = await db.execute(
                update_query,
                (worker_id, status.value, current_time, order_id, OrderStatus.NEW.value)
            )
            
            affected_rows = cursor.rowcount
            logger.info(f"Update affected {affected_rows} rows")
            
            if affected_rows == 0:
                # Додаткова перевірка, чому не оновилося
                async with db.execute("SELECT ID_order, status FROM request_order WHERE ID_order = ?", (order_id,)) as check_cursor:
                    check_row = await check_cursor.fetchone()
                    if check_row:
                        logger.warning(f"Order exists but not updated. Current status: {check_row['status']}, expected: {OrderStatus.NEW.value}")
                    else:
                        logger.warning(f"Order {order_id} not found after update attempt")
                return False
            
            # Перевіряємо, чи дійсно оновилося
            await db.commit()
            logger.info(f"Database commit successful")
            
            # Перевірка після оновлення
            async with db.execute("SELECT ID_order, status, ID_worker FROM request_order WHERE ID_order = ?", (order_id,)) as verify_cursor:
                verify_row = await verify_cursor.fetchone()
                if verify_row:
                    logger.info(f"Verification after update: {dict(verify_row)}")
                else:
                    logger.warning("Verification failed: order not found after update")
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating order status: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            if db:
                try:
                    await db.rollback()
                    logger.info("Transaction rolled back")
                except Exception as rollback_error:
                    logger.error(f"Error during rollback: {rollback_error}")
            return False
        finally:
            if db:
                try:
                    await db.close()
                    logger.info("Database connection closed")
                except Exception as close_error:
                    logger.error(f"Error closing database connection: {close_error}")


    async def complete_order(self, order_id: str) -> bool:
        """Marks an order as completed."""
        db = None
        try:
            db = await self._get_db_connection()
            current_time = datetime.now().isoformat()
            query = """
                UPDATE request_order 
                SET status = ?, completed_at = ?, updated_at = ?
                WHERE ID_order = ?
            """
            await db.execute(query, (
                OrderStatus.COMPLETED.value,
                current_time,
                current_time,
                order_id
            ))
            await db.commit()
            return True
        except Exception as e:
            logger.error(f"Error completing order {order_id}: {e}")
            return False
        finally:
            if db:
                await db.close()

    async def process_new_order(
        self, 
        user_id: int,
        username: str,
        order_data: Dict[str, Any],
        comment: str,
        bot: Bot
    ) -> Optional[str]:
        """Process new order creation and send admin notification."""
        try:
            prepared_order = {
                "ID_user": user_id,
                "subject": order_data["subject"],
                "type_work": order_data["type_work"],
                "order_details": comment,
                "status": OrderStatus.NEW.value,
                "created_at": datetime.now().isoformat()
            }
            
            new_id = await self.create_order(prepared_order)
            if not new_id:
                return None

            await self._send_admin_notification(
                bot=bot,
                order_id=new_id,
                username=username,
                order_data=prepared_order,
                comment=comment
            )
            
            return new_id
            
        except Exception as e:
            logger.error(f"Error processing new order: {e}")
            return None
            
    async def _send_admin_notification(
        self,
        bot: Bot,
        order_id: str,
        username: str,
        order_data: Dict[str, Any],
        comment: str
    ) -> None:
        """Send notification about new order to admin channel."""
        try:
            builder = InlineKeyboardBuilder()
            builder.button(
                text="Взяти замовлення", 
                callback_data=f"take_order_{order_id}"
            )
            
            admin_message = (
                f"--- Нове замовлення ---\n"
                f"<b>Час:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"<b>ID замовлення:</b> {order_id}\n"
                f"<b>Від:</b> @{username or 'Без нікнейма'}\n"
                f"<b>Предмет:</b> {order_data['subject']}\n"
                f"<b>Тип роботи:</b> {order_data['type_work']}\n"
                f"<b>Деталі замовлення:</b> {comment}\n"
                f"---------------------------"
            )
            
            await bot.send_message(
                Config.ADMIN_CHANNEL_ID,
                admin_message,
                parse_mode="HTML",
                reply_markup=builder.as_markup()
            )
            
        except Exception as e:
            logger.error(f"Error sending admin notification: {e}")
            raise