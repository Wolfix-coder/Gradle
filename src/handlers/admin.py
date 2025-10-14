from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from services.admin_service import AdminService
from services.database_service import DatabaseService
from services.order_service import OrderService
from states.user_states import UserState
from utils.decorators import require_admin
from utils.keyboards import get_admin_keyboard
from utils.logging import logger

import logging

admin_router = Router(name='admin')

admin_service = AdminService()
database_service = DatabaseService()
order_service = OrderService()

@admin_router.message(Command("admin"))
@require_admin
async def show_admin_panel(message: Message) -> None:
    await message.answer(
        "🔧 Панель керування замовленнями\n"
        "Виберіть потрібну опцію:",
        reply_markup=get_admin_keyboard().as_markup()
    )

@admin_router.callback_query(F.data == "back_to_admin")
@require_admin
async def back_to_admin(callback: CallbackQuery) -> None:
    try:
        await callback.message.edit_text(
            "🔧 Панель керування замовленнями\n"
            "Виберіть потрібну опцію:",
            reply_markup=get_admin_keyboard().as_markup()
        )
    except Exception as e:
        logging.error(f"Error returning to admin panel: {e}")
        await callback.answer("Error returning to menu", show_alert=True)

@admin_router.message(Command("status"))
@require_admin
async def status_order(message: Message) -> None:
    try:
        text = message.text
        args = admin_service.parse_command(text)
        
        if not args:
            await message.answer(text=(
                f"Неправильний формат команди!\n"
                f"Введіть команду ще раз з одним з наступних параметрів:\n"
                f"-order_id ### - пошук замовлення по ІD замовлення;\n"
                f"-order_status # - пошук замовлень по статусу роботи;\n"
                f"-pay_status # - пошук замовлень по статусу оплати;\n"
                f"-user ### - пошук замовлень по ID клієнта.\n"
            ))
            return
        
        order_id = args.get('order_id')
        filters_order_status = args.get('order_status')
        filters_pay_status = args.get('pay_status')  
        filters_user = args.get('user')

        logger.debug(f"args = {args}")

        if order_id:
            order = await database_service.get_by_id('order_request', 'ID_order', order_id)
            payment = await database_service.get_by_id('payments', 'ID_order', order_id)
            text_message = admin_service.generate_order_info_message(order['ID_order'], order['ID_user'], order['ID_worker'], order['subject'], order['type_work'], order['order_details'], payment['price'], order['status'], payment['status'])

            await message.answer(text=text_message, parse_mode='HTML')

        elif filters_order_status:
            try:
                logger.info(f"Шукаємо замовлення зі статусом: {filters_order_status}")

                # 1. Отримуємо всі замовлення за статусом  
                orders = await database_service.get_all_by_field('order_request', 'status', filters_order_status)
                logger.info(f"Знайдено замовлень: {len(orders)}")

                if not orders:
                    await message.answer("Замовлень з таким статусом не знайдено.")
                    return

                # 2. Для кожного замовлення отримуємо платежі
                for i, order in enumerate(orders):
                    logger.info(f"Обробляємо замовлення {i+1}: {order}")

                    order_id = order['ID_order']
                    logger.info(f"ID замовлення: {order_id}")

                    # Отримуємо платежі для цього ID_order
                    payments = await database_service.get_all_by_field('payments', 'ID_order', order_id)
                    logger.info(f"Знайдено платежів: {len(payments)}")
                    logger.info(f"Платежі: {payments}")

                    # Якщо є платежі
                    if payments:
                        for j, payment in enumerate(payments):
                            logger.info(f"Обробляємо платіж {j+1}: {payment}")

                            # Перевіряємо чи є потрібні поля
                            if 'price' not in payment:
                                logger.error(f"Поле 'price' відсутнє в платежі: {payment}")
                                continue
                            if 'status' not in payment:
                                logger.error(f"Поле 'status' відсутнє в платежі: {payment}")
                                continue
                            
                            text_message = admin_service.generate_order_info_message(
                                order['ID_order'], 
                                order['ID_user'], 
                                order['ID_worker'], 
                                order['subject'], 
                                order['type_work'], 
                                order['order_details'], 
                                payment['price'],
                                order['status'], 
                                payment['status']
                            )
                            logger.info("Відправляємо повідомлення...")
                            await message.answer(text=text_message, parse_mode='HTML')
                    else:
                        logger.info("Платежів немає, відправляємо без платіжної інформації")
                        await message.answer("Платежів по цьому фільтру статусу замовлення не знайдено.")

            except Exception as e:
                logger.error(f"Помилка: {e}")
                logger.error(f"Тип помилки: {type(e)}")
                import traceback
                logger.error(f"Повний traceback: {traceback.format_exc()}")
                await message.answer("Помилка при отриманні замовлень!")
                raise

        elif filters_pay_status:
            try:
                logger.info(f"Шукаємо замовлення зі статусом: {filters_pay_status}")

                # 1. Отримуємо всі замовлення за статусом  
                payments = await database_service.get_all_by_field('payments', 'status', filters_pay_status)
                logger.info(f"Знайдено замовлень: {len(payments)}")

                if not payments:
                    await message.answer("Замовлень з таким статусом не знайдено.")
                    return

                # 2. Для кожного замовлення отримуємо платежі
                for i, payment in enumerate(payments):
                    logger.info(f"Обробляємо замовлення {i+1}: {payment}")

                    order_id = payment['ID_order']
                    logger.info(f"ID замовлення: {order_id}")

                    # Отримуємо платежі для цього ID_order
                    orders = await database_service.get_all_by_field('order_request', 'ID_order', order_id)
                    logger.info(f"Знайдено платежів: {len(orders)}")
                    logger.info(f"Платежі: {orders}")

                    # Якщо є платежі
                    if orders:
                        for j, order in enumerate(orders):
                            logger.info(f"Обробляємо платіж {j+1}: {order}")

                            # Перевіряємо чи є потрібні поля
                            if 'ID_user' not in order:
                                logger.error(f"Поле 'ID_user' відсутнє в платежі: {order}")
                                continue
                            if 'ID_worker' not in order:
                                logger.error(f"Поле 'ID_worker' відсутнє в платежі: {order}")
                                continue
                            if 'subject' not in order:
                                logger.error(f"Поле 'subject' відсутнє в платежі: {order}")
                                continue
                            if 'type_work' not in order:
                                logger.error(f"Поле 'type_worker' відсутнє в платежі: {order}")
                                continue
                            if 'order_details' not in order:
                                logger.error(f"Поле 'order_details' відсутнє в платежі: {order}")
                                continue
                            if 'status' not in order:
                                logger.error(f"Поле 'status' відсутнє в платежі: {order}")
                                continue
                            
                            text_message = admin_service.generate_order_info_message(
                                order['ID_order'], 
                                order['ID_user'], 
                                order['ID_worker'], 
                                order['subject'], 
                                order['type_work'], 
                                order['order_details'], 
                                payment['price'],
                                order['status'], 
                                payment['status']
                            )
                            logger.info("Відправляємо повідомлення...")
                            await message.answer(text=text_message, parse_mode='HTML')
                    else:
                        logger.info("Платежів немає, відправляємо без платіжної інформації")
                        await message.answer("Платежів по цьому фільтру статусу оплати не знайдено.")

            except Exception as e:
                logger.error(f"Помилка: {e}")
                logger.error(f"Тип помилки: {type(e)}")
                import traceback
                logger.error(f"Повний traceback: {traceback.format_exc()}")
                await message.answer("Помилка при отриманні замовлень!")
                raise
       
        elif filters_user:
            try:
                logger.info(f"Шукаємо замовлення зі статусом: {filters_user}")

                # 1. Отримуємо всі замовлення за статусом  
                orders = await database_service.get_all_by_field('order_request', 'ID_user', filters_user)
                logger.info(f"Знайдено замовлень: {len(orders)}")

                if not orders:
                    await message.answer("Замовлень з таким статусом не знайдено.")
                    return

                # 2. Для кожного замовлення отримуємо платежі
                for i, order in enumerate(orders):
                    logger.info(f"Обробляємо замовлення {i+1}: {order}")

                    order_id = order['ID_order']
                    logger.info(f"ID замовлення: {order_id}")

                    # Отримуємо платежі для цього ID_order
                    payments = await database_service.get_all_by_field('payments', 'ID_order', order_id)
                    logger.info(f"Знайдено платежів: {len(payments)}")
                    logger.info(f"Платежі: {payments}")

                    # Якщо є платежі
                    if payments:
                        for j, payment in enumerate(payments):
                            logger.info(f"Обробляємо платіж {j+1}: {payment}")

                            # Перевіряємо чи є потрібні поля
                            if 'price' not in payment:
                                logger.error(f"Поле 'price' відсутнє в платежі: {payment}")
                                continue
                            if 'status' not in payment:
                                logger.error(f"Поле 'status' відсутнє в платежі: {payment}")
                                continue
                            
                            text_message = admin_service.generate_order_info_message(
                                order['ID_order'], 
                                order['ID_user'], 
                                order['ID_worker'], 
                                order['subject'], 
                                order['type_work'], 
                                order['order_details'], 
                                payment['price'],
                                order['status'], 
                                payment['status']
                            )
                            logger.info("Відправляємо повідомлення...")
                            await message.answer(text=text_message, parse_mode='HTML')
                    else:
                        logger.info("Платежів немає, відправляємо без платіжної інформації")
                        await message.answer("Платежів для цього фільтру по користувачам не знайдено.")

            except Exception as e:
                logger.error(f"Помилка: {e}")
                logger.error(f"Тип помилки: {type(e)}")
                import traceback
                logger.error(f"Повний traceback: {traceback.format_exc()}")
                await message.answer("Помилка при отриманні замовлень!")
                raise

    except Exception as e:
        logger.error(f"eroor: {e}")
        raise

@admin_router.message(Command("search"))
@require_admin
async def search_user(message: Message):
    """Пошук користувача за ID"""
    try:
        try:
            text = message.text
            args = admin_service.parse_command(text)

            if not args:
                await message.answer(text=(
                    f"<b>Неправильний формат команди.</b>\n"
                    f"Команда повинна мати фільтр:\n"
                    f"/search -id ### - пошук данних за id.\n"
                    f"/search -link @### - пошук за username.\n"
                ), parse_mode="HTML")
                return

            user_id = args.get('id')
            user_link = admin_service.parse_at_tags(args.get('link'))

        except Exception as e:
            logger.error(f"Помилка під час парсингу параметрів команди /search : {e}")
            logger.debug(f"args: = {args}")
            logger.debug(f"user_id: = {user_id}")
            logger.debug(f"user_link: = {user_link}")
            raise

        try:
            if user_id:
                user_info = await database_service.get_by_id("user_data", "ID", user_id)

                if not user_info:
                    await message.answer(text="Користувача не знайдено в системі.")
                    return

                text_message = admin_service.generate_user_info_message(user_info['ID'],
                                                                        user_info['user_name'],
                                                                        user_info['user_link'],
                                                                        user_info['real_full_name'],
                                                                        user_info['for_father'],
                                                                        user_info['education'],
                                                                        user_info['course'],
                                                                        user_info['edu_group'],
                                                                        user_info['phone_number'],
                                                                        user_info['language_code'],
                                                                        user_info['created_at'])
                await message.answer(text=text_message, parse_mode="HTML")
        except Exception as e:
            logger.error(f"Сталася помилка під час виконнаня команди /search з параметром -user_id {user_id}: {e}")
            raise

        try:
            if user_link:
                user_info = await database_service.get_by_id("user_data", "user_link", user_link)

                if not user_info:
                    await message.answer(text="Користувача не знайдено в системі.")
                    return

                text_message = admin_service.generate_user_info_message(user_info['ID'],
                                                                        user_info['user_name'],
                                                                        user_info['user_link'],
                                                                        user_info['real_full_name'],
                                                                        user_info['for_father'],
                                                                        user_info['education'],
                                                                        user_info['course'],
                                                                        user_info['edu_group'],
                                                                        user_info['phone_number'],
                                                                        user_info['language_code'],
                                                                        user_info['created_at'])
                await message.answer(text=text_message, parse_mode="HTML")
        except Exception as e:
            logger.error(f"Сталася помилка під час виконнаня команди /search з параметром -user_link {user_link}: {e}")
            raise
        
    except Exception as e:
        logger.error(f"Помилка при спробі пошуку користувача: {e}")
        raise

@admin_router.message(Command("send_message"))
@require_admin
async def send_message(message: Message, state: FSMContext):
    "Відправлення повідомлення користувачу"
    try:
        try:
            """Перевірка аргументів команди"""
            text = message.text
            args = admin_service.parse_command(text)

            if not args:
                    await message.answer(text=(
                        f"<b>Неправильний формат команди!</b>\n\n"
                        f"Використовуйте один із варіантів:\n"
                        f"▫️ <code>/send_message -id ### -text ###</code> — надіслати повідомлення за ID користувача\n"
                        f"▫️ <code>/send_message -link @### -text ###</code> — надіслати повідомлення за user_link\n\n"
                        f"<b>Пояснення параметрів:</b>\n"
                        f"   • <code>-id ###</code> — ID користувача\n"
                        f"   • <code>-link @###</code> — посилання (username) користувача\n"
                        f"   • <code>-text ###</code> — текст повідомлення\n"

                    ), parse_mode="HTML")
                    return

            if not args.get('id'):
                user_data = await database_service.get_by_id('user_data', 'user_link', admin_service.parse_at_tags(args.get('link')))
                user_id = user_data['ID']
            else:
                if not args.get('link'):
                    user_id = args.get('id')
                else:
                    await message.answer(text=(
                        f"<b>Неправильний формат команди!</b>\n\n"
                        f"Використовуйте один із варіантів:\n"
                        f"▫️ <code>/send_message -id ### -text ###</code> — надіслати повідомлення за ID користувача\n"
                        f"▫️ <code>/send_message -link @### -text ###</code> — надіслати повідомлення за user_link\n\n"
                        f"<b>Пояснення параметрів:</b>\n"
                        f"   • <code>-id ###</code> — ID користувача\n"
                        f"   • <code>-link @###</code> — посилання (username) користувача\n"
                        f"   • <code>-text ###</code> — текст повідомлення\n"

                    ), parse_mode="HTML")
                    return

            if not args.get('text'):
                await message.answer(text=(
                        f"<b>Неправильний формат команди!</b>\n\n"
                        f"Використовуйте один із варіантів:\n"
                        f"▫️ <code>/send_message -id ### -text ###</code> — надіслати повідомлення за ID користувача\n"
                        f"▫️ <code>/send_message -link @### -text ###</code> — надіслати повідомлення за user_link\n\n"
                        f"<b>Пояснення параметрів:</b>\n"
                        f"   • <code>-id ###</code> — ID користувача\n"
                        f"   • <code>-link @###</code> — посилання (username) користувача\n"
                        f"   • <code>-text ###</code> — текст повідомлення\n"

                    ), parse_mode="HTML")
                return

            text_message = args.get('text')

            await state.set_state(UserState.waiting_for_reply_data)
            await state.update_data(history=text_message)

        except Exception as e:
            logger.error(f"Помилка при отриманні параметрів команди /send_message: {e}")
            logger.debug(f"user_id: = {user_id}")
            logger.debug(f"text_message: = {text_message}")
            raise
        
        try:
            admin_id = message.from_user.id

            builder = InlineKeyboardBuilder()
            builder.button(text="Відповісти", callback_data=f"reply_message_user:{user_id}:{admin_id}")

            admin_data = await database_service.get_by_id('user_data', 'ID', admin_id)

            await message.bot.send_message(chat_id=user_id, text=(f"Адміністратор: @{admin_data['user_link']} надіслав вам повідомлення."))
            await message.bot.send_message(chat_id=user_id, text=text_message, parse_mode='HTML', reply_markup=builder.as_markup())

            await message.bot.send_message(chat_id=admin_id, text="Повідомлення успішно відправлено")

            await state.clear()
        except Exception as e:
            await message.answer(f"Виникла помилка при надсиланні листа. Спробуйте пізніше.")
            logger.error(f"Помилка при надсиланні повідомлення командою /send_message: {e}")
            raise
        
    except Exception as e:
            logger.error(f"Помилка команди /send_message: {e}")

@admin_router.callback_query(F.data.startswith("reply_message_admin:"))
async def reply_message_admin(callback: CallbackQuery, state: FSMContext):
    try:
        user_id = callback.from_user.id
        admin_id = callback.data.split(':', 2)[2]

        await state.set_state(UserState.waiting_for_reply_data)
        await state.update_data(user_id=user_id, admin_id=admin_id)

        await callback.message.answer(f"Надішліть відповідь користувачу в наступному повідомлені.")
    except Exception as e:
        await callback.answer(f"Ой! Виникла помилка. Спробуйте пізніше.")
        logger.error(f"Помилка при відповіді на калбек кнопку reply_message з боку адміна: {e}")

@admin_router.callback_query(F.data.startswith("reply_message_admin:"))
async def send_message_to_admin(callback: CallbackQuery, state: FSMContext):
    try:
        data = await state.get_data()

        user_id = data.get("user_id")
        admin_id = data.get("admin_id")
        history_text = data.get("history")

        builder = InlineKeyboardBuilder()
        builder.button(text="Відповісти", callback_data=f"reply_message_user:{user_id}:{admin_id}")

        await callback.message.bot.send_message(chat_id=user_id, text=(
            f"<blockquote> {history_text} </blockquote>\n"
            f"Повідомлення ->\n"
            f"{callback.message.text}\n"
            ), parse_mode="HTML", reply_markup=builder.as_markup())
        
        await callback.message.bot.send_message(chat_id=admin_id, text="Повідомлення успішно відправлено")

        await state.clear()

    except Exception as e:
            await callback.message.answer(f"Виникла помилка при надсиланні листа. Спробуйте пізніше.")
            logger.error(f"Помилка при надсиланні відповіді на повідомлення калбек кнопкою з боку юзера: {e}")
            raise