import re

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command

from services.admin_service import AdminService
from services.database_service import DatabaseService
from services.order_service import OrderService
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
async  def status_order(message: Message) -> None:
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
            text_message = admin_service.generate_message(order['ID_order'], order['ID_user'], order['ID_worker'], order['subject'], order['type_work'], order['order_details'], payment['price'], order['status'], payment['status'])

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
                            
                            text_message = admin_service.generate_message(
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
                        await message.answer("Платежів для цього замовлення не знайдено.")

            except Exception as e:
                logger.error(f"Помилка: {e}")
                logger.error(f"Тип помилки: {type(e)}")
                import traceback
                logger.error(f"Повний traceback: {traceback.format_exc()}")
                await message.answer("Помилка при отриманні замовлень!")
        elif filters_pay_status:
                    pass
        elif filters_user:
            pass



    except Exception as e:
        logger.error(f"eroor: {e}")
        raise