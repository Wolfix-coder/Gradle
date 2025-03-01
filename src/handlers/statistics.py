import logging
import aiosqlite

from aiogram import Router, types
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from typing import Dict, List, Tuple
from datetime import datetime

from utils.decorators import require_admin
from services.order_service import OrderService
from utils.keyboards import get_admin_keyboard

from model.order import Order, OrderStatus
from config import Config

statistics_router = Router(name='statistics')

@statistics_router.callback_query(lambda c: c.data == "my_statistics")
@require_admin
async def show_statistics(callback: CallbackQuery) -> None:
    """
    Показує статистику для адміністратора.
    """
    try:
        worker_id = callback.from_user.id
        order_service = OrderService()
        
        stats = await order_service.get_worker_statistics(worker_id)
        
        stats_text = (
            f"📊 Ваша статистика:\n\n"
            f"✅ Всього виконано замовлень: {stats['total_completed']}\n"
            f"📝 Активних замовлень: {stats['active_orders']}\n\n"
            f"📚 Топ предметів:\n"
        )

        for subject, count in stats['top_subjects']:
            stats_text += f"- {subject}: {count} замовлень\n"

        keyboard = InlineKeyboardBuilder()
        keyboard.button(text="🔙 Назад", callback_data="back_to_admin")

        await callback.message.edit_text(
            stats_text,
            reply_markup=keyboard.as_markup()
        )

    except Exception as e:
        logging.error(f"Помилка при показі статистики: {e}")
        await callback.message.edit_text(
            "Сталася помилка при отриманні статистики. Спробуйте пізніше.",
            reply_markup=get_admin_keyboard().as_markup()
        )

class OrderService:
    def __init__(self):
        self.db_path = Config.DATABASE_PATH

    async def get_worker_statistics(self, worker_id: int) -> Dict:
        """
        Отримує статистику для конкретного працівника.
        
        Args:
            worker_id (int): ID працівника
            
        Returns:
            Dict: Словник зі статистикою, що містить:
                - total_completed: загальна кількість виконаних замовлень
                - active_orders: кількість активних замовлень
                - top_subjects: список кортежів (предмет, кількість замовлень)
        """
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                
                # Отримуємо кількість виконаних замовлень
                async with db.execute("""
                    SELECT COUNT(*) as count 
                    FROM request_order 
                    WHERE ID_worker = ? AND status = ?
                """, (worker_id, OrderStatus.COMPLETED.value)) as cursor:
                    completed = await cursor.fetchone()
                    total_completed = completed['count']

                # Отримуємо кількість активних замовлень
                async with db.execute("""
                    SELECT COUNT(*) as count 
                    FROM request_order 
                    WHERE ID_worker = ? AND status = ?
                """, (worker_id, OrderStatus.IN_PROGRESS.value)) as cursor:
                    active = await cursor.fetchone()
                    active_orders = active['count']

                # Отримуємо топ предметів
                async with db.execute("""
                    SELECT subject, COUNT(*) as count 
                    FROM request_order 
                    WHERE ID_worker = ? AND status = ?
                    GROUP BY subject 
                    ORDER BY count DESC 
                    LIMIT 5
                """, (worker_id, OrderStatus.COMPLETED.value)) as cursor:
                    subjects = await cursor.fetchall()
                    top_subjects = [(row['subject'], row['count']) for row in subjects]

                return {
                    'total_completed': total_completed,
                    'active_orders': active_orders,
                    'top_subjects': top_subjects
                }
                
        except Exception as e:
            logging.error(f"Помилка при отриманні статистики для працівника {worker_id}: {e}")
            raise