import aiosqlite
import logging
from datetime import datetime

from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

# Відносні імпорти для правильної структури проекту
from utils.decorators import require_admin
from utils.keyboards import get_worker_order_keyboard, subject_keyboard, type_work_keyboard
from services.order_service import OrderService
from states.order_states import OrderStates
from services.database import DatabaseService
from model.order import OrderStatus, Order
from utils.logging import logger
from config import Config
from config import Config as MAX_COMMENT_LENGTH
from config import Config as ADMIN_CHANNEL_ID
from text import type_work_text
from utils.validators import validate_input


# Створюємо роутер
users_orders_router = Router()
admin_orders_router = Router()

# Ініціалізуємо сервіс
order_service = OrderService()


@admin_orders_router.callback_query(F.data == "new_orders")
@require_admin
async def show_new_orders(callback: CallbackQuery) -> None:
    """Показує список нових замовлень."""
    try:
        orders = await order_service.get_new_orders()
        
        if not orders:
            keyboard = InlineKeyboardBuilder()
            keyboard.button(text="🔙 Назад", callback_data="back_to_admin")
            await callback.message.edit_text(
                "У вас немає нових замовлень.",
                reply_markup=keyboard.as_markup()
            )
            return

        await callback.message.delete()

        for order in orders:
            keyboard = InlineKeyboardBuilder()
            keyboard.button(text="✅ Взяти замовлення", callback_data=f"take_order_{order.ID_order}")
            keyboard.button(text="🔙 Назад", callback_data="back_to_admin")
            keyboard.adjust(1)

            order_text = (
                f"📌 Замовлення #{order.ID_order}\n"
                f"📚 Предмет: {order.subject}\n"
                f"📝 Тип роботи: {order.type_work}\n"
                f"📋 Деталі: {order.order_details}\n"
                f"👤 Замовник: @{order.user_link}\n"
                f"📅 Створено: {order.created_at}"
            )

            await callback.message.answer(order_text, reply_markup=keyboard.as_markup())

    except Exception as e:
        logging.error(f"Помилка при показі нових замовлень: {e}")
        keyboard = InlineKeyboardBuilder()
        keyboard.button(text="🔙 Назад", callback_data="back_to_admin")
        await callback.message.edit_text(
            "Сталася помилка при отриманні нових замовлень.",
            reply_markup=keyboard.as_markup()
        )

@admin_orders_router.callback_query(lambda c: c.data == "my_orders")
@require_admin
async def handle_my_orders(callback: CallbackQuery):
    """Обробляє запит на перегляд замовлень працівника."""
    await show_worker_orders_handler(callback)

@admin_orders_router.callback_query(lambda c: c.data == "refresh_worker_orders")
@require_admin
async def handle_refresh_orders(callback: CallbackQuery):
    """Оновлює список замовлень працівника."""
    await show_worker_orders_handler(callback)

@admin_orders_router.callback_query(F.data.startswith("take_order_"))
@require_admin
async def take_order(callback: CallbackQuery) -> None:
    """Обробляє взяття замовлення адміністратором."""
    try:
        # Отримуємо ID замовлення з callback даних
        order_id = callback.data.split('_', 2)[2]
        worker_id = callback.from_user.id
        worker_username = callback.from_user.username or 'без_імені'
        
        # Перевіряємо статус замовлення безпосередньо в БД
        async with aiosqlite.connect(Config.DATABASE_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT status FROM request_order WHERE ID_order = ?", 
                (order_id,)
            ) as cursor:
                result = await cursor.fetchone()
                
                if not result:
                    logger.warning(f"Замовлення {order_id} не знайдено при спробі взяття")
                    await callback.answer("Замовлення не знайдено.", show_alert=True)
                    return
                
                current_status = result['status']
                logger.info(f"Поточний статус замовлення {order_id}: {current_status}")
                
                # Перевіряємо, чи статус = 1 (NEW)
                if current_status != 1:
                    logger.info(f"Спроба взяти вже взяте замовлення {order_id} користувачем {worker_id}")
                    await callback.answer("Це замовлення вже взято іншим виконавцем.", show_alert=True)
                    return
                
                # Оновлюємо статус замовлення на 2 (IN_PROGRESS) і встановлюємо виконавця
                try:
                    await db.execute(
                        "UPDATE request_order SET status = 2, ID_worker = ? WHERE ID_order = ?",
                        (worker_id, order_id)
                    )
                    await db.commit()
                except Exception as e:
                    logger.error(f"Помилка при оновленні статусу замовлення: {e}")
                    await callback.answer("Не вдалося взяти замовлення. Спробуйте пізніше.", show_alert=True)
                    return
        
        # Створюємо клавіатуру для оновленого повідомлення
        keyboard = InlineKeyboardBuilder()
        keyboard.button(text="📋 Мої активні замовлення", callback_data="my_active_orders")
        keyboard.button(text="🔙 Назад", callback_data="back_to_admin")
        keyboard.adjust(1)  # Розміщуємо кнопки в один стовпчик

        # Оновлюємо повідомлення з інформацією про взяття замовлення
        await callback.message.edit_text(
            f"{callback.message.text}\n\n✅ Замовлення взято в роботу адміністратором @{worker_username}!",
            reply_markup=keyboard.as_markup()
        )
        
        # Повідомляємо адміністратора про успішне взяття замовлення
        await callback.answer("Замовлення успішно взято!", show_alert=True)
        
        logger.info(f"Замовлення {order_id} успішно взято адміністратором {worker_id} (@{worker_username})")

    except Exception as e:
        logger.error(f"Помилка при взятті замовлення: {e}", exc_info=True)
        await callback.answer("Помилка при взятті замовлення. Спробуйте пізніше.", show_alert=True)
        
async def get_worker_orders(worker_id: int) -> list:
    """
    Отримує всі замовлення працівника з бази даних.
    
    Args:
        worker_id (int): ID працівника
        
    Returns:
        list: Список замовлень
    """
    try:
        async with aiosqlite.connect(Config.DATABASE_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT 
                    ro.ID_order,
                    ro.subject,
                    ro.type_work,
                    ro.order_details,
                    ro.created_at,
                    ro.status,
                    u.user_name,
                    u.user_link
                FROM request_order ro
                LEFT JOIN users u ON ro.ID_user = u.ID
                WHERE ro.ID_worker = ? 
                AND ro.status IN (?, ?)
                ORDER BY 
                    CASE ro.status 
                        WHEN ? THEN 1 
                        WHEN ? THEN 2 
                    END,
                    ro.created_at DESC
            """, (worker_id, 
                  OrderStatus.IN_PROGRESS.value,
                  OrderStatus.NEW.value,
                  OrderStatus.IN_PROGRESS.value,
                  OrderStatus.NEW.value)) as cursor:
                return [dict(row) for row in await cursor.fetchall()]
    except Exception as e:
        logging.error(f"Помилка отримання замовлень воркера: {e}")
        return []

async def show_worker_orders_handler(callback: CallbackQuery) -> None:
    """Показує всі замовлення працівника."""
    try:
        worker_id = callback.from_user.id
        orders = await get_worker_orders(worker_id)

        if not orders:
            keyboard = InlineKeyboardBuilder()
            keyboard.button(text="🔄 Оновити", callback_data="refresh_worker_orders")
            keyboard.button(text="🔙 Назад", callback_data="back_to_admin")
            await callback.message.edit_text(
                "У вас немає активних замовлень.",
                reply_markup=keyboard.as_markup()
            )
            return

        await callback.message.delete()

        for order in orders:
            order_text = (
                f"📌 Замовлення #{order['ID_order']}\n"
                f"📚 Предмет: {order['subject']}\n"
                f"📝 Тип роботи: {order['type_work']}\n"
                f"👤 Замовник: @{order['user_link']}\n"
                f"📅 Створено: {order['created_at']}\n"
                f"📋 Деталі: {order['order_details']}\n"
                f"Статус: {'🔄 В роботі' if order['status'] == OrderStatus.IN_PROGRESS.value else '🆕 Нове'}"
            )
            
            keyboard = get_worker_order_keyboard(order['ID_order'])
            keyboard.button(text="🔄 Оновити", callback_data="refresh_worker_orders")
            keyboard.button(text="🔙 Назад", callback_data="back_to_admin")
            keyboard.adjust(1)
            
            await callback.message.answer(
                order_text,
                reply_markup=keyboard.as_markup()
            )

    except Exception as e:
        logging.error(f"Помилка відображення замовлень воркера: {e}")
        keyboard = InlineKeyboardBuilder()
        keyboard.button(text="🔙 Назад", callback_data="back_to_admin")
        await callback.message.edit_text(
            "Сталася помилка при отриманні замовлень.",
            reply_markup=keyboard.as_markup()
        )

@admin_orders_router.callback_query(F.data.startswith("send_work_"))
async def send_work_to_client(callback: CallbackQuery, state: FSMContext) -> None:
    """Ініціює процес відправки виконаної роботи клієнту."""
    try:
        order_id = str(callback.data.split("_")[1])
        await state.set_state(OrderStates.AWAITING_WORK)
        await state.update_data(order_id=order_id, files=[])
        
        keyboard = InlineKeyboardBuilder()
        keyboard.button(text="✅ Завершити відправку", callback_data=f"finish_sending_{order_id}")
        keyboard.button(text="❌ Скасувати", callback_data=f"cancel_send_{order_id}")
        
        await callback.message.edit_text(
            "📤 Надішліть файли, фото, відео або текстові повідомлення.\n"
            "Натисніть 'Завершити відправку', коли закінчите",
            reply_markup=keyboard.as_markup()
        )
        
    except Exception as e:
        logging.error(f"Помилка при ініціації відправки роботи: {e}")
        await callback.answer("Помилка при початку процесу відправки", show_alert=True)

@admin_orders_router.callback_query(F.data.startswith("complete_order_"))
@require_admin
async def complete_order(callback: CallbackQuery) -> None:
    """Позначає замовлення як виконане."""
    try:
        order_id = str(callback.data.split("_")[1])
        worker_id = callback.from_user.id
        
        await order_service.complete_order(order_id)
        
        keyboard = InlineKeyboardBuilder()
        keyboard.button(text="📋 Мої активні замовлення", callback_data="my_active_orders")
        keyboard.button(text="🔙 Назад", callback_data="back_to_admin")
        keyboard.adjust(1)

        await callback.message.edit_text(
            f"{callback.message.text}\n\n✅ Замовлення виконано!",
            reply_markup=keyboard.as_markup()
        )
        await callback.answer("Замовлення позначено як виконане!", show_alert=True)

    except Exception as e:
        logging.error(f"Помилка при завершенні замовлення: {e}")
        await callback.answer("Помилка при завершенні замовлення", show_alert=True)

@users_orders_router.message(Command("order"))
async def cmd_order(message: types.Message):
    try:
        if not await DatabaseService.check_user_exists(message.from_user.id):
            await message.answer("Спочатку потрібно зареєструватися. Використайте команду /start")
            return
            
        builder = InlineKeyboardBuilder()
        builder.button(text="Так", callback_data="yes")
        builder.button(text="Ні", callback_data="no")
        await message.answer(
            "Натисни на кнопку, щоб підтвердити дію та перейти до оформлення замовлення:",
            reply_markup=builder.as_markup()
        )
    except Exception as e:
        logger.error(f"Error in order command: {e}")
        await message.answer("Виникла помилка. Спробуйте пізніше.")

@users_orders_router.callback_query(F.data == "no")
async def callback_no(query: CallbackQuery):
    await query.answer("Оформлення замовлення скасовано!")
    await query.message.delete()
    await query.message.answer("Введіть команду /help, щоб ознайомитися зі списком команд.")

@users_orders_router.callback_query(F.data == "yes")
async def callback_yes(query: CallbackQuery, state: FSMContext):
    try:
        await query.answer("Оформлення замовлення розпочато!")
        await query.message.delete()
        await state.set_state(OrderStates.waiting_for_type)
        await query.message.answer("Оберіть предмет:", reply_markup=subject_keyboard())
    except Exception as e:
        logger.error(f"Error in yes callback: {e}")
        await query.message.answer("Виникла помилка. Спробуйте пізніше.")
        await state.clear()

@users_orders_router.callback_query(OrderStates.waiting_for_type)
async def process_subject(callback: CallbackQuery, state: FSMContext):
    try:
        await state.update_data(subject=callback.data)
        await callback.message.answer(
            type_work_text,
            reply_markup=type_work_keyboard()
        )
        await state.set_state(OrderStates.waiting_for_details)
    except Exception as e:
        logger.error(f"Error in process_subject: {e}")
        await callback.message.answer("Виникла помилка. Спробуйте пізніше.")
        await state.clear()

@users_orders_router.callback_query(OrderStates.waiting_for_details)
async def process_type(callback: CallbackQuery, state: FSMContext):
    try:
        await state.update_data(type_work=callback.data)
        await callback.message.answer(
            "Введіть коментар до замовлення (в одному повідомленні):"
        )
        await state.set_state(OrderStates.waiting_for_comment)
    except Exception as e:
        logger.error(f"Error in process_type: {e}")
        await callback.message.answer("Виникла помилка. Спробуйте пізніше.")
        await state.clear()

@users_orders_router.message(OrderStates.waiting_for_comment)
async def process_details(message: Message, state: FSMContext):
    try:
        # Валідація коментаря
        comment = validate_input(message.text, Config.MAX_COMMENT_LENGTH)
        if not comment:
            await message.answer(
                f"Некоректний коментар. Спробуйте ще раз (максимум {Config.MAX_COMMENT_LENGTH} символів)"
            )
            return

        # Отримуємо дані зі стану
        data = await state.get_data()
        
        # Готуємо дані замовлення з правильними назвами полів
        order_data = {
            "ID_user": message.from_user.id,  # Виправлено на великий регістр
            "subject": data["subject"],
            "type_work": data["type_work"],
            "order_details": comment,
            "status": OrderStatus.NEW.value,  # Використовуємо enum
            "created_at": datetime.now().isoformat()
        }
        
        # Створюємо замовлення через сервіс
        new_id = await order_service.create_order(order_data)
        if not new_id:
            raise ValueError("Failed to create order")

        # Відправляємо повідомлення адміну
        builder = InlineKeyboardBuilder()
        builder.button(
            text="Взяти замовлення", 
            callback_data=f"take_order_{new_id}"
        )
        
        admin_message = (
            f"--- Нове замовлення ---\n"
            f"<b>Час:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"<b>ID замовлення:</b> {new_id}\n"
            f"<b>Від:</b> @{message.from_user.username or 'Без нікнейма'}\n"
            f"<b>Предмет:</b> {data['subject']}\n"
            f"<b>Тип роботи:</b> {data['type_work']}\n"
            f"<b>Деталі замовлення:</b> {comment}\n"
            f"---------------------------"
        )
        
        await message.bot.send_message(
            Config.ADMIN_CHANNEL_ID,
            admin_message,
            parse_mode="HTML",
            reply_markup=builder.as_markup()
        )
        
        await message.answer("Ваше замовлення успішно створено та відправлено на обробку!")
        await state.clear()
        
    except Exception as e:
        logger.error(f"Error in process_details: {e}")
        await message.answer("Виникла помилка при створенні замовлення. Спробуйте пізніше.")
        await state.clear()