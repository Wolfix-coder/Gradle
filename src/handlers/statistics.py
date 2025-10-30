from aiogram import Router
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from services.database_service import DatabaseService
from utils.decorators import require_admin
from utils.keyboards import get_admin_keyboard
from utils.logging import get_logger

from config import Config

# Створення роутерів
statistics_router = Router(name='statistics')

logger = get_logger("handlers/statics")

# Створення об'єктів сервісів
database_service = DatabaseService()

@statistics_router.callback_query(lambda c: c.data == "my_statistics")
@require_admin
async def show_statistics(callback: CallbackQuery) -> None:
    """
    Показує статистику для адміністратора.
    """
    try:
        worker_id = callback.from_user.id
        
        
        stats = await database_service.get_worker_statistics(worker_id)
        
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
        logger.exception(f"Помилка при показі статистики: ")
        await callback.message.edit_text(
            "Сталася помилка при отриманні статистики. Спробуйте пізніше.",
            reply_markup=get_admin_keyboard().as_markup()
        )

class OrderServicePayments:
    def __init__(self):
        self.db_path = Config.DATABASE_PATH

    