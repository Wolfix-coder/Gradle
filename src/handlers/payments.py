from aiogram import Router, types, F
from aiogram.enums import ParseMode
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

from model.payments import Payments
from services.database_service import DatabaseService
from services.payment_service import PaymentService
from utils.decorators import require_admin
from utils.keyboards import get_user_pay_keyboard
from utils.logging import logger

from config import Config
from text import help_text

# Створюємо роутер
user_payments_router = Router()
admin_payments_router = Router()

# Створюємо об'єкти сервісів
database_service = DatabaseService()
payment_service = PaymentService()

# Команда /pay для звичайного користувача
@user_payments_router.message(Command("pay"))
async def user_pay_command(message: types.Message):
    "Комадна /pay з боку користувача"

    await message.answer(
        "🔧 Панель керування оплатою замовлень\n"
        "Виберіть потрібну опцію:",
        reply_markup=get_user_pay_keyboard().as_markup()
    )

@user_payments_router.callback_query(F.data == "unpaid_order")
async def show_unpaid_order(callback: CallbackQuery) -> None:
    """Показує список не оплачених замовлень."""
    try:
        client_id = callback.from_user.id

        unpaid_payments = await payment_service.get_unpaid_orders(client_id, 0)
         

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
            payment_status = "❌ Не оплачено" if int(payment.status) == 0 else "✅ Оплачено"
            order = await database_service.get_by_id('order_request', 'ID_order', payment.ID_order)

            payment_text = (
                f"📌 Замовлення #{payment.ID_order}\n"
                f"📚 Предмет: {order.subject}\n"
                f"📝 Тип роботи: {order.type_work}\n"
                f"💰 Ціна: {payment.price} грн\n"
                f"💳 Статус оплати: {payment_status}\n"
                f"📅 Створено: {order.created_at}\n"
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

@user_payments_router.callback_query(F.data == "back_to_home")
async def back_home (callback: CallbackQuery) -> None:
    """Повертає користувача в головне меню (/help)"""
    try:
        await callback.message.answer(help_text, reply_markup=types.ReplyKeyboardRemove())
    
    except Exception as e:
        logger.error(f"Помилка при переході до головного меню юзера: {e}")
        await callback.message.answer("Виникла помилка при переході назад. Будь ласка, введіть команду /help.")

@user_payments_router.callback_query(F.data.startswith("pay_order_"))
async def pay_order(callback: CallbackQuery) -> None:
    """Процес оплати"""
    try:
        await callback.answer()

        order_id = str(callback.data.split('_', 2)[2])  # Витяг номера замовлення для оплати
        

        # Отримуємо всі поля БД за ключем order_id
        payment = await database_service.get_by_id('payments', 'ID_order', order_id)

        if not payment:
            logger.warning(f"Замовлення {order_id} не знайдено при спробі оплати")
            await callback.answer("Замовлення не знайдено.", show_alert=True)
            return
            
        # Перевірка статусу - якщо статус не 0 (неоплачено), то замовлення вже оплачено
        if int(payment.status) != 0:
            logger.info(f"Замовлення {order_id} вже оплачено.")
            await callback.answer("Це замовлення вже оплачено.", show_alert=True)
            return
            
        try:
            keyboard = InlineKeyboardBuilder()
            keyboard.button(text="Оплатити", callback_data=f"paid_{payment.ID_order}")

            money = payment.price - payment.paid
            
            await callback.message.answer(
                text=(
                    f"💳 <b>Оплата</b>\n\n"
                    f"Переведіть <b>{money} грн</b> на картку:\n"
                    f"<code>{Config.PAYMENT_TOKEN}</code>\n\n"
                    f"Після переказу коштів натисніть кнопку нижче, щоб повідомити адміністратора.\n\n"
                    f"<i>Для копіювання номера картки просто натисніть на неї.</i>"
                ),
                parse_mode="HTML",
                reply_markup=keyboard.as_markup()
            )

        except Exception as e:
            logger.error(f"Помилка процесу оплати: {e}")
            await callback.message.answer()
    
    except ValueError:
        logger.error(f"Невірний формат order_id: {callback.data}")
        await callback.answer("Помилка в номері замовлення.", show_alert=True)
    except Exception as e:
        logger.error(f"Помилка при обробці оплати: {e}")
        await callback.answer("Виникла помилка при обробці оплати.", show_alert=True)

@user_payments_router.callback_query(F.data.startswith("paid_"))
async def notify_admin_about_payment(callback: CallbackQuery) -> None:
    """Відправлення повідомлення адміністратору про виконану оплату"""
    try:
        user_id = callback.from_user.id
        order_id = str(callback.data.split('_', 1)[1])  # Витяг номера замовлення для оплати

        # Отримуємо всі поля за order_id
        order = await database_service.get_by_id('order_request', 'ID_order', order_id)
        payment = await database_service.get_by_id('payments', 'ID_order', order_id)

        money = payment.price - payment.paid

        keyboard = InlineKeyboardBuilder()
        keyboard.button(text="Підтвердити", callback_data=f"confirm_{order_id}")
        keyboard.button(text="Відхилити", callback_data=f"reject_{order_id}")
        
        # Відправляємо повідомлення адміністратору
        await callback.answer()
        await callback.bot.send_message(
            text=(
                f"🧾 Новий запит на перевірку оплати\n\n"
                f"👤 Користувач: <code>{user_id}</code>\n"
                f"🆔 Замовлення: <b>{order_id}</b>\n"
                f"💰 Сума: <b>{money} грн</b>\n\n"
                f"Перевірте оплату й підтвердьте вручну."
            ),
            chat_id=int(order.ID_worker),
            parse_mode="HTML",
            reply_markup=keyboard.as_markup()
        )
    except Exception as e:
        logger.error(f"Помилка при відправці повідомлення адміністратору для підтвердження оплати: {e}")
        await callback.answer("Щось пішло не так. Спробуйте ще раз або зверніться в підтримку командою /support.", show_alert=True)

@user_payments_router.callback_query(F.data.startswith("confirm_"))
async def confirm_pay(callback: CallbackQuery) -> None:
    """Підтвердження від адміністратора про сплату"""
    try:
        await callback.answer()

        # Витяг id замовлення з callback запиту  
        order_id = callback.data.split('_', 1)[1]

        # Отримання замовлення
        payment = await database_service.get_by_id('payments', 'ID_order', order_id)
        order = await database_service.get_by_id('order_request', 'ID_order', order_id)

        if not payment and not order:
            await callback.message.answer(f"Замовлення {order_id} не знайдено")
            return
        
        if payment.status != 0:
            await callback.message.answer(f"Замовлення {order_id} вже оплачено")
            return

        # Позначення як оплачене
        success = await payment_service.mark_confirm_pay(order_id)

        if success == True:
            logger.info(f"Замовлення {order_id} оплачено.")
            await callback.message.answer(f"Замовлення {order_id} оплачено.")  # Повідомлення адміну
            
            await callback.bot.send_message(
                chat_id=order.ID_user, 
                text=f"Ваше замовлення {order_id} було успішно оплачено."  # Повідомлення користувачу
            )
        else:
            await callback.message.answer(f"Не вдалося оновити статус замовлення {order_id}.")

    except Exception as e:
        logger.error(f"Помилка при підтвердженні оплати замовлення {order_id}: {e}")
        await callback.message.answer("Сталася помилка під час обробки платежу.")