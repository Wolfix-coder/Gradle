import aiosqlite
import traceback

from typing import List, Optional, Dict, Any
from datetime import datetime
from aiogram import Bot

from aiogram.utils.keyboard import InlineKeyboardBuilder
from model.order import Order, OrderStatus

from config import Config
from utils.logging import logger

class OrderService:
    
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
        """Отримує певне замовлення за ідентифікатором з інформацією про користувача."""
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

            query = """
                INSERT INTO payments (
                    ID_order, status, created_at
                ) VALUES (?, ?, ?)
            """

            await db.execute(query, (
                new_id,
                False,
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


    async def in_progress_order(self, order_id: str, worker_id: int) -> bool:
        db = None
        try:
            db = await self._get_db_connection()
            current_time = datetime.now().isoformat()
            query = """
                UPDATE request_order 
                SET status = ?, ID_worker = ?, updated_at = ?
                WHERE ID_order = ?
            """

            await db.execute(query, (
                OrderStatus.IN_PROGRESS.value,
                worker_id,
                current_time,
                order_id
            ))
            await db.commit()
            return True
        
        except Exception as e:
            logger.error(f"Error update status order {order_id} IN_PROGRESS: {e}")
            return False
        finally:
            if db:
                await db.close()


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
            logger.error(f"Error update status order {order_id} COMPLETED: {e}")
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
        """Створення нового замовлення та надсилання повідомлення адміністратору."""
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