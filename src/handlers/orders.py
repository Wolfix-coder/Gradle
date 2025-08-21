import aiosqlite
import logging
from datetime import datetime

from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.exceptions import TelegramBadRequest

from model.order import OrderStatus
from services.database_service import DatabaseService
from services.order_service import OrderService
from states.order_states import OrderStates
from utils.logging import logger
from utils.decorators import require_admin
from utils.keyboards import get_worker_order_keyboard, subject_keyboard, type_work_keyboard
from utils.validators import validate_input

from config import Config
from text import type_work_text

# Створюємо роутер
users_orders_router = Router()
admin_orders_router = Router()

# Ініціалізуємо сервіс
database_service = DatabaseService()
order_service = OrderService()


@admin_orders_router.callback_query(F.data == "new_orders")
@require_admin
async def show_new_orders(callback: CallbackQuery) -> None:
    """Показує список нових замовлень."""
    try:
        orders = await database_service.get_all_by_field('order',)
        
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
        order_id = callback.data.split('_', 2)[2] # Витяг номер замовлення
        worker_id = callback.from_user.id # Витяг ID працівника який натиснув на кнопку
        worker_username = callback.from_user.username or 'без_імені' # Витяг ім'я працівника

        # Створюємо екземпляр класу DatabaseService
        database_service = DatabaseService()
        
        # Отримуємо замовлення та перевіряємо його статус
        order = await database_service.get_by_id(order_id)
        
        if not order:
            logger.warning(f"Замовлення {order_id} не знайдено при спробі взяття")
            await callback.answer("Замовлення не знайдено.", show_alert=True)
            return
            
        if order.status != 1:
            "Перевірка статусу замовлення"
            logger.info(f"Спроба взяти вже взяте замовлення {order_id} користувачем {worker_id}")
            await callback.answer("Це замовлення вже взято іншим виконавцем.", show_alert=True)
            return
        
        # Створюємо екземпляр класу OrderService
        order_service = OrderService()
        
        # Оновлюємо статус замовлення через сервіс
        success = await order_service.in_progress_order(
            order_id=order_id,
            worker_id=worker_id
        )
        
        if not success:
            logger.error(f"Не вдалося оновити статус замовлення {order_id}")
            await callback.answer("Не вдалося взяти замовлення. Спробуйте пізніше.", show_alert=True)
            return
        
        # Створюємо клавіатуру для оновленого повідомлення
        keyboard = InlineKeyboardBuilder()
        keyboard.button(text="📋 Мої активні замовлення", callback_data="my_orders")
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
                    o.ID_order,
                    o.subject,
                    o.type_work,
                    o.order_details,
                    o.created_at,
                    o.status,
                    u.user_name,
                    u.user_link
                FROM order o
                LEFT JOIN user_data u ON o.ID_user = u.ID
                WHERE o.ID_worker = ? 
                AND o.status IN (?, ?)
                ORDER BY 
                    CASE o.status 
                        WHEN ? THEN 1 
                        WHEN ? THEN 2 
                    END,
                    o.created_at DESC
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

        # Створюємо клавіатуру для повідомлення
        keyboard = InlineKeyboardBuilder()
        keyboard.button(text="🔄 Оновити", callback_data="refresh_worker_orders")
        keyboard.button(text="🔙 Назад", callback_data="back_to_admin")
        keyboard.adjust(1)

        if not orders:
            try:
                # Спробуємо оновити існуюче повідомлення
                await callback.message.edit_text(
                    "У вас немає активних замовлень.",
                    reply_markup=keyboard.as_markup()
                )
            except TelegramBadRequest as e:
                # Якщо повідомлення не змінилося, просто відповідаємо користувачу
                if "message is not modified" in str(e):
                    await callback.answer("У вас немає активних замовлень", show_alert=True)
                else:
                    # Якщо інша помилка, пробуємо видалити і відправити нове
                    await callback.message.delete()
                    await callback.message.answer(
                        "У вас немає активних замовлень.",
                        reply_markup=keyboard.as_markup()
                    )
            return

        # Видаляємо поточне повідомлення перед відправкою нових
        try:
            await callback.message.delete()
        except Exception as e:
            logger.warning(f"Не вдалося видалити повідомлення: {e}")

        # Відправляємо нові повідомлення для кожного замовлення
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
            
            order_keyboard = get_worker_order_keyboard(order['ID_order'])
            order_keyboard.button(text="🔄 Оновити", callback_data="refresh_worker_orders")
            order_keyboard.button(text="🔙 Назад", callback_data="back_to_admin")
            order_keyboard.adjust(1)
            
            await callback.message.answer(
                order_text,
                reply_markup=order_keyboard.as_markup()
            )

    except Exception as e:
        logging.error(f"Помилка відображення замовлень воркера: {e}", exc_info=True)
        try:
            keyboard = InlineKeyboardBuilder()
            keyboard.button(text="🔙 Назад", callback_data="back_to_admin")
            await callback.message.edit_text(
                "Сталася помилка при отриманні замовлень.",
                reply_markup=keyboard.as_markup()
            )
        except Exception as edit_error:
            # Якщо не вдалося відредагувати, спробуємо відправити нове повідомлення
            logger.error(f"Додаткова помилка при спробі відредагувати повідомлення: {edit_error}")
            await callback.answer("Сталася помилка при отриманні замовлень", show_alert=True)

@admin_orders_router.callback_query(F.data.startswith("send_work_"))
async def send_work_to_client(callback: CallbackQuery, state: FSMContext) -> None:
    """Ініціює процес відправки виконаної роботи клієнту."""
    try:
        order_id = str(callback.data.split("_")[2])
        await state.set_state(OrderStates.AWAITING_WORK)
        await state.update_data(order_id=order_id, files=[], messages=[])
        
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


@admin_orders_router.message(OrderStates.AWAITING_WORK, F.text)
async def handle_text_for_client(message: Message, state: FSMContext) -> None:
    """Обробляє текстові повідомлення для відправки клієнту."""
    try:
        data = await state.get_data()
        messages = data.get("messages", [])
        messages.append({"type": "text", "content": message.text})
        await state.update_data(messages=messages)
        
        await message.answer("✅ Текстове повідомлення додано до черги відправки")
    except Exception as e:
        logging.error(f"Помилка при обробці текстового повідомлення: {e}")
        await message.answer("❌ Помилка при додаванні повідомлення")


@admin_orders_router.message(OrderStates.AWAITING_WORK, F.photo)
async def handle_photo_for_client(message: Message, state: FSMContext) -> None:
    """Обробляє фото для відправки клієнту."""
    try:
        data = await state.get_data()
        files = data.get("files", [])
        
        photo = message.photo[-1]  # Беремо найбільшу версію фото
        file_id = photo.file_id
        
        caption = message.caption if message.caption else ""
        
        files.append({"type": "photo", "file_id": file_id, "caption": caption})
        await state.update_data(files=files)
        
        await message.answer("✅ Фото додано до черги відправки")
    except Exception as e:
        logging.error(f"Помилка при обробці фото: {e}")
        await message.answer("❌ Помилка при додаванні фото")


@admin_orders_router.message(OrderStates.AWAITING_WORK, F.document)
async def handle_document_for_client(message: Message, state: FSMContext) -> None:
    """Обробляє документи для відправки клієнту."""
    try:
        data = await state.get_data()
        files = data.get("files", [])
        
        file_id = message.document.file_id
        caption = message.caption if message.caption else ""
        
        files.append({"type": "document", "file_id": file_id, "caption": caption})
        await state.update_data(files=files)
        
        await message.answer("✅ Документ додано до черги відправки")
    except Exception as e:
        logging.error(f"Помилка при обробці документа: {e}")
        await message.answer("❌ Помилка при додаванні документа")


@admin_orders_router.message(OrderStates.AWAITING_WORK, F.video)
async def handle_video_for_client(message: Message, state: FSMContext) -> None:
    """Обробляє відео для відправки клієнту."""
    try:
        data = await state.get_data()
        files = data.get("files", [])
        
        file_id = message.video.file_id
        caption = message.caption if message.caption else ""
        
        files.append({"type": "video", "file_id": file_id, "caption": caption})
        await state.update_data(files=files)
        
        await message.answer("✅ Відео додано до черги відправки")
    except Exception as e:
        logging.error(f"Помилка при обробці відео: {e}")
        await message.answer("❌ Помилка при додаванні відео")


@admin_orders_router.message(OrderStates.AWAITING_WORK, F.voice)
async def handle_voice_for_client(message: Message, state: FSMContext) -> None:
    """Обробляє голосові повідомлення для відправки клієнту."""
    try:
        data = await state.get_data()
        files = data.get("files", [])
        
        file_id = message.voice.file_id
        
        files.append({"type": "voice", "file_id": file_id})
        await state.update_data(files=files)
        
        await message.answer("✅ Голосове повідомлення додано до черги відправки")
    except Exception as e:
        logging.error(f"Помилка при обробці голосового повідомлення: {e}")
        await message.answer("❌ Помилка при додаванні голосового повідомлення")
        
@admin_orders_router.callback_query(F.data.startswith("finish_sending_"))
async def finish_sending_work(callback: CallbackQuery, state: FSMContext) -> None:
    """Завершує процес відправки роботи та надсилає всі файли клієнту."""
    try:
        order_id = callback.data.split("_")[2]
        data = await state.get_data()
        files = data.get("files", [])
        messages = data.get("messages", [])
        
        # Отримуємо інформацію про замовлення
        order = await database_service.get_by_id('request_order', 'ID_order', order_id)
            
        if not order:
            await callback.answer("Замовлення не знайдено", show_alert=True)
            await state.clear()
            return
        
        client_id = order.ID_user
        send_errors = []
        
        # Надсилаємо повідомлення клієнту про виконану роботу
        try:
            await callback.bot.send_message(
                client_id,
                f"✅ Ваше замовлення #{order_id} виконано!\n\n"
                f"Нижче ви отримаєте всі матеріали від виконавця."
            )
        except Exception as e:
            logger.error(f"Помилка при надсиланні початкового повідомлення: {e}")
            send_errors.append("початкове повідомлення")
        
        # Надсилаємо текстові повідомлення
        for i, msg in enumerate(messages):
            if msg["type"] == "text":
                try:
                    await callback.bot.send_message(client_id, msg["content"])
                except Exception as e:
                    logger.error(f"Помилка при надсиланні текстового повідомлення #{i+1}: {e}")
                    send_errors.append(f"текстове повідомлення #{i+1}")
        
        # Надсилаємо файли
        for i, file in enumerate(files):
            try:
                if file["type"] == "photo":
                    await callback.bot.send_photo(
                        client_id, 
                        file["file_id"],
                        caption=file["caption"] if file["caption"] else None
                    )
                elif file["type"] == "document":
                    await callback.bot.send_document(
                        client_id, 
                        file["file_id"],
                        caption=file["caption"] if file["caption"] else None
                    )
                elif file["type"] == "video":
                    await callback.bot.send_video(
                        client_id, 
                        file["file_id"],
                        caption=file["caption"] if file["caption"] else None
                    )
                elif file["type"] == "voice":
                    await callback.bot.send_voice(client_id, file["file_id"])
            except Exception as e:
                logger.error(f"Помилка при надсиланні файлу #{i+1} типу {file['type']}: {e}")
                send_errors.append(f"файл #{i+1} ({file['type']})")

        try:
            keyboard = InlineKeyboardBuilder()
            keyboard.button(text="✅ Все ОК", callback_data=f"complete_order_{order_id}")
            keyboard.button(text="❌ Потрібні правки", callback_data=f"fix_work_{order_id}")

            await callback.bot.send_message(
                client_id,
                "Підтвердіть виконання роботи.",
                reply_markup=keyboard.as_markup()
            )
        except Exception as e:
            logger.error(f"Помилка при надсиланні повідомлення підтвердження виконання роботи (463): {e}")
            await callback.answer("Помилка при надсиланні повідомлення підтвердження виконання роботи", show_alert=True)
        
        # Очищаємо стан
        await state.clear()
        
    except Exception as e:
        logger.error(f"Помилка при завершенні відправки роботи: {e}")
        await callback.answer("Помилка при відправці матеріалів клієнту", show_alert=True)
        await state.clear()

@admin_orders_router.callback_query(F.data.startswith("cancel_send_"))
async def cancel_sending_work(callback: CallbackQuery, state: FSMContext) -> None:
    """Скасовує процес відправки роботи."""
    try:
        order_id = callback.data.split("_")[2]
        
        await callback.message.edit_text(
            f"❌ Відправку матеріалів для замовлення #{order_id} скасовано."
        )
        
        await state.clear()
        
    except Exception as e:
        logging.error(f"Помилка при скасуванні відправки роботи: {e}")
        await callback.answer("Помилка при скасуванні відправки", show_alert=True)
        await state.clear()
        
@admin_orders_router.callback_query(F.data.startswith("complete_order_"))
async def complete_order(callback: CallbackQuery, state: FSMContext) -> None:
    """Позначає замовлення як виконане."""
    try:
        order_id = str(callback.data.split("_")[2])
        
        # Отримуємо інформацію про замовлення
        order = await database_service.get_by_id('request_order', 'ID_order', order_id)

        worker_id = order.ID_worker
        client_id = order.ID_user

        await order_service.complete_order(order_id)
        
        keyboard = InlineKeyboardBuilder()
        keyboard.button(text="📋 Мої активні замовлення", callback_data="my_orders")
        keyboard.button(text="🔙 Назад", callback_data="back_to_admin")
        keyboard.adjust(1)

        await callback.bot.send_message(
            worker_id,
            f"✅ Замовлення виконано!",
            reply_markup=keyboard.as_markup()
        )
        await callback.answer("Замовлення позначено як виконане!", show_alert=True)

        await callback.bot.send_message(
            client_id,
            text = (
                f"✅ Замовлення #{order_id} позначено як виконане."
                f" Дякуємо що обираєте нас!"
            )
        )

        await state.clear()

    except Exception as e:
        logging.error(f"Помилка при завершенні замовлення: {e}")
        await callback.answer("Помилка при завершенні замовлення", show_alert=True)

@users_orders_router.message(Command("order"))
async def cmd_order(message: types.Message):
    try:
        if not await database_service.get_by_id('user_data', 'ID', message.from_user.id):
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
        
        # Готуємо дані замовлення
        order_data = {
            "subject": data["subject"],
            "type_work": data["type_work"],
        }

        # Створюємо екземпляр класу OrderService
        order_service = OrderService() 
        
        # Використовуємо сервіс для створення замовлення та відправки повідомлення адміну
        new_id = await order_service.process_new_order(
            user_id=message.from_user.id,
            username=message.from_user.username or 'Без нікнейма',
            order_data=order_data,
            comment=comment,
            bot=message.bot
        )
        
        # if not new_id:
        #     raise ValueError("Не вдалося створити замовлення")

        await message.answer("Ваше замовлення успішно створено та відправлено на обробку!")
        await state.clear()
        
    except Exception as e:
        logger.error(f"Помилка в process_details: {e}")
        await message.answer("Виникла помилка при створенні замовлення. Спробуйте пізніше")
        await state.clear()

# async def get_orders_with_users(self, status: str) -> List[Dict]: # type: ignore
#         """
#         Отримати замовлення разом з даними користувачів
    
#         Args:
#             status: str - статус замовлень ('pending', 'completed', etc.)
    
#         Returns:
#             List[Dict] - список замовлень з даними користувачів
#         """
    
#         # 1. Отримуємо всі замовлення по статусу
#         orders = await self.get_orders_with_users()
    
#         # 2. Для кожного замовлення додаємо дані користувача
#         for order in orders:
#             user = await self.get_by_id('user_data', 'ID', order['ID_user'])
        
#             # Додаємо дані користувача до замовлення
#             if user:
#                 order['user_name'] = user['user_name']
#                 order['user_link'] = user['user_link']
#             else:
#                 # Якщо користувача не знайдено
#                 order['user_name'] = None
#                 order['user_link'] = None
    
#         return orders

