from aiogram import Router, types, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

from model.payments import Payments
from services.database import DatabaseService
from services.payment_service import PaymentService
from utils.decorators import require_admin
from utils.keyboards import get_user_pay_keyboard
from utils.logging import logger

# Створюємо роутер
payments_router = Router()

# Команда /pay для звичайного користувача
@payments_router.message(Command("pay"))
async def user_pay_command(message: types.Message):
    "Комадна /pay з боку користувача"

    await message.answer(
        "🔧 Панель керування оплатою замовлень\n"
        "Виберіть потрібну опцію:",
        reply_markup=get_user_pay_keyboard().as_markup()
    )

@payments_router.callback_query(F.data == "unpaid_order")
async def show_unpaid_order(callback: CallbackQuery) -> None:
    """Показує список не оплачених замовлень."""
    try:
        payment_service = PaymentService()
        unpaid_payments = await payment_service.get_unpaid_orders()

        if not unpaid_payments:
            keyboard = InlineKeyboardBuilder()
            keyboard.button(text="🔙 Назад", callback_data="back_to_home")
            await callback.message.edit_text(
                "У вас немає не оплачених замовлень.",
                reply_markup=keyboard.as_markup()
            )
            return
        
        await callback.message.delete()
        
        # Проходимо по кожному платежу і відправляємо окреме повідомлення
        for payment in unpaid_payments:
            keyboard = InlineKeyboardBuilder()
            keyboard.button(text="💰 Оплатити", callback_data=f"pay_order_{payment.ID_order}")
            keyboard.button(text="🔙 Назад", callback_data="back_to_home")
            keyboard.adjust(2, 1)

            # Визначаємо статус оплати для кожного платежу
            payment_status = "❌ Не оплачено" if payment.status == 0 else "✅ Оплачено"
                    
            payment_text = (
                f"📌 Замовлення #{payment.ID_order}\n"
                f"📚 Предмет: {payment.subject}\n"
                f"📝 Тип роботи: {payment.type_work}\n"
                f"💰 Ціна: {payment.price} грн\n"
                f"💳 Статус оплати: {payment_status}\n"
                f"📅 Створено: {payment.created_at}\n"
            )
                    
            await callback.message.answer(
                payment_text,
                reply_markup=keyboard.as_markup()
            )

    except Exception as e:
        logger.error(f"Error showing unpaid orders: {e}")
        await callback.message.answer(
            "❌ Помилка при отриманні не оплачених замовлень.",
            reply_markup=get_user_pay_keyboard().as_markup()
        )