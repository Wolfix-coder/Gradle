from datetime import datetime

from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from services.database_service import DatabaseService
from services.payment_service import PaymentService
from states.payments_state import PaymentStates
from utils.decorators import require_admin
from utils.dict import work_dict
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
                f"📚 Предмет: {work_dict.subjects.get(order['subject'], order['subject'])}\n"
                f"📝 Тип роботи: {work_dict.type_work.get(order['type_work'], order['type_work'])}\n"
                f"💰 Ціна: {payment.price} грн\n"
                f"💳 Статус оплати: {payment_status}\n"
                f"📅 Створено: {order['created_at']}\n"
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
        if int(payment['status']) != 0:
            logger.info(f"Замовлення {order_id} вже оплачено.")
            await callback.answer("Це замовлення вже оплачено.", show_alert=True)
            return
            
        try:
            keyboard = InlineKeyboardBuilder()
            keyboard.button(text="Оплатити", callback_data=f"paid_{payment['ID_order']}")

            money = payment['price']
            
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

        await callback.message.delete()

        await callback.bot.send_message(user_id, text="Запит на перевірку оплати  надіслано адміністрації.")

        # Отримуємо всі поля за order_id
        order = await database_service.get_by_id('order_request', 'ID_order', order_id)
        payment = await database_service.get_by_id('payments', 'ID_order', order_id)

        money = payment['price']

        keyboard = InlineKeyboardBuilder()
        keyboard.button(text="Підтвердити", callback_data=f"confirm_pay_{order_id}")
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
            chat_id=int(order['ID_worker']),
            parse_mode="HTML",
            reply_markup=keyboard.as_markup()
        )
    except Exception as e:
        logger.error(f"Помилка при відправці повідомлення адміністратору для підтвердження оплати: {e}")
        await callback.answer("Щось пішло не так. Спробуйте ще раз або зверніться в підтримку командою /support.", show_alert=True)

@admin_payments_router.callback_query(F.data.startswith("reject_"))
async def reject_pay(callback: CallbackQuery) -> None:
    try:
        await callback.answer()
        await callback.message.delete()

        order_id = callback.data.split('_', 1)[1]
        order = await database_service.get_by_id('order_request', 'ID_order', order_id)

        await callback.bot.send_message(chat_id=order['ID_user'],
                                        text=(
                                            f"Схоже що адміністратор відхилив ваш запрос на підтвердження оплати.\n"
                                            f"Будь ласка, перевірте чи ви перевели повну суму роботи.\n"
                                            f"Якщо адміністратор вже декілька разів відхилив вашу заявку, будь ласка, напишіть нам в підтримку /support ."
                                        ), reply_markup=get_user_pay_keyboard().as_markup())
        
        await callback.bot.send_message(chat_id=order['ID_worker'], text="Заявка успішно відхилина.")
    except Exception as e:
        logger.error(f"Помилка при відхилені заяіки на оплату reject_pay(): {e}")
        raise

@user_payments_router.callback_query(F.data.startswith("confirm_pay_"))
async def confirm_pay(callback: CallbackQuery) -> None:
    """Підтвердження від адміністратора про сплату"""
    try:
        await callback.answer()

        # Витяг id замовлення з callback запиту  
        order_id = callback.data.split('_', 2)[2]

        # Отримання замовлення
        payment = await database_service.get_by_id('payments', 'ID_order', order_id)
        order = await database_service.get_by_id('order_request', 'ID_order', order_id)

        if not payment and not order:
            await callback.message.answer(f"Замовлення {order_id} не знайдено")
            return
        
        if int(payment['status']) != 0:
            logger.info(payment['status'])
            await callback.message.answer(f"Замовлення {order_id} вже оплачено")
            return

        # Позначення як оплачене
        success = await payment_service.mark_confirm_pay(order_id)

        if success == True:
            logger.info(f"Замовлення {order_id} оплачено.")
            await callback.message.answer(f"Замовлення {order_id} оплачено.")  # Повідомлення адміну
            
            await callback.bot.send_message(
                chat_id=order['ID_user'], 
                text=f"Ваше замовлення {order_id} було успішно оплачено."  # Повідомлення користувачу
            )
        else:
            await callback.message.answer(f"Не вдалося оновити статус замовлення {order_id}.")

    except Exception as e:
        logger.error(f"Помилка при підтвердженні оплати замовлення {order_id}: {e}")
        await callback.message.answer("Сталася помилка під час обробки платежу.")

@admin_payments_router.callback_query(F.data.startswith("put_price_"))
@require_admin
async def put_price(callback: CallbackQuery, state: FSMContext) -> None:
    try:
        await callback.answer()

        # Витяг id замовлення з callback запиту  
        order_id = callback.data.split('_', 2)[2]

        await callback.message.answer(f"В наступному повідомленні надайте повну ціну данного замовлення (#{order_id}).\n Повідомлення повинне бути в числовому форматі та округлено до сотих. Наприклад 12.34")

        await state.set_state(PaymentStates.AWAITING_PRICE)
        await state.update_data(order_id=order_id)

    except Exception as e:
        logger.error(f"Помилка при спробі відображення меню встановлення ціни: {e}")
        await callback.message.answer("Проблеми з відображенням меню. \n Спробуйте трохи пізніше.")
        await state.clear()

@admin_payments_router.message(PaymentStates.AWAITING_PRICE)
async def await_price(message: Message, state: FSMContext) -> None:
    try:
        try:
            price = round(float(message.text.replace(',', '.')), 2)
        except ValueError:
            await message.answer("Невірний формат ціни. Приклад: 12.34")
            return
        
        await state.update_data(price=price)
        payment_detail = await state.get_data()

        payment_request_status = await payment_service.write_price(payment_detail["order_id"], payment_detail["price"])
        
        if not payment_request_status:
            await message.answer("Виникла помилка. Спробуйте пізніше.")
        else:

            await message.answer("Все ОК) Дані додані до бази данних.")

            keyboard = InlineKeyboardBuilder()
            keyboard.button(text="Оплатити", callback_data=f"pay_order_{payment_detail['order_id']}")
            keyboard.adjust(1)

            order = await database_service.get_by_id("order_request", "ID_order", payment_detail["order_id"])
            user_data = await database_service.get_by_id("user_data", "ID", order["ID_worker"])

            client_message = (
                f"--- Замовлення оновлено ---\n"
                f"<b>Час:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"<b>ID замовлення:</b> {order['ID_order']}\n"
                f"<b>Від:</b> @{order['ID_user'] or 'Без нікнейма'}\n"
                f"<b>Виконавець:</b> @{user_data['user_link'] or 'Без нікнейм'}\n"
                f"<b>Предмет:</b> {work_dict.subjects.get(order['subject'], order['subject'])}\n"
                f"<b>Тип роботи:</b> {work_dict.type_work.get(order['type_work'], order['type_work'])}\n"
                f"<b>Деталі замовлення:</b> {order['order_details']}\n"
                f"<b>Ціна:</b> {payment_detail['price']}\n"
                f"---------------------------"
            )

            await message.answer(text=client_message, parse_mode="HTML")
            await message.bot.send_message(chat_id=order['ID_user'], 
                                           text=client_message, 
                                           parse_mode="HTML",
                                           reply_markup=keyboard.as_markup())

            await state.clear()
    except Exception as e:
        logger.error(f"Помилка додавання ціни в стани: {e}")
        await message.answer("Щось пішло не так. \nСпробуйте ще раз пізніше.")
        await state.clear()
