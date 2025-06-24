from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
import logging

from utils.decorators import require_admin
from services.database import DatabaseService
from services.payment_service import PaymentService
from model.order import OrderStatus

# Створюємо роутер
payments_router = Router()

# Ініціалізуємо сервіс платежів
payment_service = PaymentService()

@payments_router.message(Command("pay"))
async def initiate_payment(message: Message) -> None:
    try:
        if not await DatabaseService.check_user_exists(message.from_user.id):
            await message.answer("Спочатку потрібно зареєструватися. Використайте команду /start")
            return
        
        unpaid_orders = await payment_service.get_unpaid_orders(message.from_user.id)
        
        if not unpaid_orders:
            await message.answer("У вас немає замовлень, що потребують оплати.")
            return
        
        keyboard = InlineKeyboardBuilder()
        for order in unpaid_orders:
            keyboard.button(
                text=f"Замовлення {order.order_id}: {order.total_price} UAH", 
                callback_data=f"payment_{order.order_id}"
            )
        keyboard.adjust(1)
        
        await message.answer(
            "Оберіть замовлення для оплати:", 
            reply_markup=keyboard.as_markup()
        )
        
    except Exception as e:
        logging.error(f"Помилка при ініціації оплати: {e}")
        await message.answer("Помилка при перевірці замовлень")

@payments_router.message(Command("setpayment"))
@require_admin
async def set_order_payment(message: Message) -> None:
    try:
        parts = message.text.split()
        if len(parts) != 4:
            await message.answer(
                "Invalid command format. "
                "Use: /setpayment -id [order_id] -p [amount]"
            )
            return

        if parts[1] != '-id' or parts[3] != '-p':
            await message.answer("Invalid command format.")
            return
            
        order_id = parts[2]
        payment = float(parts[4])
        
        await payment_service.set_order_payment(order_id, payment)
        await message.answer(f"✅ Set price {payment} UAH for order {order_id}")
        
    except ValueError as e:
        await message.answer(f"❌ Error: {str(e)}")
    except Exception as e:
        logging.error(f"Error setting payment: {e}")
        await message.answer("❌ Error setting payment")