from model.order import OrderStatus
from .database import DBConnection
from datetime import datetime
import logging
from typing import Optional, Dict, List

class PaymentError(Exception):
    """Base class for payment-related errors"""
    pass

class InsufficientFundsError(PaymentError):
    """Raised when payment amount is insufficient"""
    pass

class InvalidPaymentError(PaymentError):
    """Raised when payment data is invalid"""
    pass

class PaymentService:
    def __init__(self):
        self.db = DBConnection()

    async def set_order_price(self, order_id: str, price: float) -> bool:
        """Set total price for an order"""
        try:
            async with self.db.connection() as conn:
                if price <= 0:
                    raise InvalidPaymentError("Ціна повинна бути більше 0")

                query = """
                    UPDATE request_order 
                    SET total_price = ?,
                        updated_at = ?
                    WHERE ID_order = ?
                """
                await conn.execute(query, (
                    price,
                    datetime.now().isoformat(),
                    order_id
                ))
                await conn.commit()
                return True

        except Exception as e:
            logging.error(f"Error setting order price: {e}")
            raise

    # Решта методів залишаються без змін
    async def record_payment(self, order_id: str, amount: float) -> bool:
        try:
            async with self.db.connection() as conn:
                query = """
                    SELECT total_price, paid_amount, status
                    FROM request_order
                    WHERE ID_order = ?
                """
                async with conn.execute(query, (order_id,)) as cursor:
                    order_data = await cursor.fetchone()

                if not order_data:
                    raise PaymentError("Замовлення не знайдено")

                total_price, current_paid, status = order_data

                if amount <= 0:
                    raise InvalidPaymentError("Сума платежу повинна бути більше 0")

                new_paid_amount = current_paid + amount

                if new_paid_amount > total_price:
                    raise InvalidPaymentError("Сума платежу перевищує вартість замовлення")

                update_query = """
                    UPDATE request_order 
                    SET paid_amount = ?,
                        updated_at = ?
                    WHERE ID_order = ?
                """
                await conn.execute(update_query, (
                    new_paid_amount,
                    datetime.now().isoformat(),
                    order_id
                ))
                await conn.commit()
                return True

        except Exception as e:
            logging.error(f"Error recording payment: {e}")
            raise

    async def record_payment(self, order_id: str, amount: float) -> bool:
        """Record a payment for an order"""
        try:
            async with self.db.connection() as conn:
                # Get current order info
                query = """
                    SELECT total_price, paid_amount, status
                    FROM request_order
                    WHERE ID_order = ?
                """
                async with conn.execute(query, (order_id,)) as cursor:
                    order_data = await cursor.fetchone()

                if not order_data:
                    raise PaymentError("Замовлення не знайдено")

                total_price, current_paid, status = order_data

                # Validate payment
                if amount <= 0:
                    raise InvalidPaymentError("Сума платежу повинна бути більше 0")

                new_paid_amount = current_paid + amount

                if new_paid_amount > total_price:
                    raise InvalidPaymentError("Сума платежу перевищує вартість замовлення")

                # Update paid amount
                update_query = """
                    UPDATE request_order 
                    SET paid_amount = ?,
                        updated_at = ?
                    WHERE ID_order = ?
                """
                await conn.execute(update_query, (
                    new_paid_amount,
                    datetime.now().isoformat(),
                    order_id
                ))
                await conn.commit()
                return True

        except Exception as e:
            logging.error(f"Error recording payment: {e}")
            raise

    async def get_payment_status(self, order_id: str) -> Dict:
        """Get payment status for an order"""
        try:
            async with self.db.connection() as conn:
                query = """
                    SELECT total_price, paid_amount, status
                    FROM request_order
                    WHERE ID_order = ?
                """
                async with conn.execute(query, (order_id,)) as cursor:
                    order_data = await cursor.fetchone()

                if not order_data:
                    raise PaymentError("Замовлення не знайдено")

                total_price, paid_amount, status = order_data
                remaining = total_price - paid_amount

                return {
                    "order_id": order_id,
                    "total_price": total_price,
                    "paid_amount": paid_amount,
                    "remaining": remaining,
                    "is_fully_paid": paid_amount >= total_price,
                    "status": status
                }

        except Exception as e:
            logging.error(f"Error getting payment status: {e}")
            raise

    async def get_unpaid_orders(self, user_id: int) -> List[Dict]:
        """Get list of orders that require payment"""
        try:
            async with self.db.connection() as conn:
                query = """
                    SELECT ID_order, total_price, paid_amount, status
                    FROM request_order 
                    WHERE ID_user = ? 
                    AND paid_amount < total_price
                    AND status != ?
                    ORDER BY created_at DESC
                """
                async with conn.execute(query, (
                    user_id, 
                    OrderStatus.CANCELLED.value
                )) as cursor:
                    orders = await cursor.fetchall()

                return [{
                    "order_id": order[0],
                    "total_price": order[1],
                    "paid_amount": order[2],
                    "remaining": order[1] - order[2],
                    "status": order[3]
                } for order in orders]

        except Exception as e:
            logging.error(f"Error getting unpaid orders: {e}")
            raise

    async def process_refund(self, order_id: str, amount: float) -> bool:
        """Process refund for an order"""
        try:
            async with self.db.connection() as conn:
                # Get current payment info
                query = """
                    SELECT paid_amount, status
                    FROM request_order
                    WHERE ID_order = ?
                """
                async with conn.execute(query, (order_id,)) as cursor:
                    order_data = await cursor.fetchone()

                if not order_data:
                    raise PaymentError("Замовлення не знайдено")

                current_paid, status = order_data

                # Validate refund
                if amount <= 0:
                    raise InvalidPaymentError("Сума повернення повинна бути більше 0")

                if amount > current_paid:
                    raise InvalidPaymentError("Сума повернення перевищує сплачену суму")

                # Process refund
                new_paid_amount = current_paid - amount
                update_query = """
                    UPDATE request_order 
                    SET paid_amount = ?,
                        updated_at = ?,
                        status = ?
                    WHERE ID_order = ?
                """
                await conn.execute(update_query, (
                    new_paid_amount,
                    datetime.now().isoformat(),
                    OrderStatus.CANCELLED.value,
                    order_id
                ))
                await conn.commit()
                return True

        except Exception as e:
            logging.error(f"Error processing refund: {e}")
            raise

    async def get_payment_statistics(self, worker_id: Optional[int] = None) -> Dict:
        """Get payment statistics"""
        try:
            async with self.db.connection() as conn:
                base_query = """
                    SELECT 
                        COUNT(*) as total_orders,
                        SUM(total_price) as total_amount,
                        SUM(paid_amount) as total_paid,
                        AVG(total_price) as avg_order_price
                    FROM request_order
                    WHERE status != ?
                """
                
                params = [OrderStatus.CANCELLED.value]
                
                if worker_id:
                    base_query += " AND ID_worker = ?"
                    params.append(worker_id)

                async with conn.execute(base_query, params) as cursor:
                    stats = await cursor.fetchone()

                return {
                    "total_orders": stats[0],
                    "total_amount": stats[1] or 0,
                    "total_paid": stats[2] or 0,
                    "average_order_price": stats[3] or 0,
                    "pending_payments": stats[1] - stats[2] if stats[1] and stats[2] else 0
                }

        except Exception as e:
            logging.error(f"Error getting payment statistics: {e}")
            raise