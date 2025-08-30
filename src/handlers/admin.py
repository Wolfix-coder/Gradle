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
                f"--order_id ### - пошук замовлення по ІD замовлення;\n"
                f"--all - відображення всіх замовлень, що є в системі;\n"
                f"--order_status # - пошук замовлень по статусу роботи;\n"
                f"--pay_status # - пошук замовлень по статусу оплати;\n"
                f"--user ### - пошук замовлень по ID клієнта.\n"
            ))
            return
        
        order_id = args.get('order_id')
        show_all = args.get('all', False)
        filters_order_status = args.get('order_status')
        filters_pay_status = args.get('pay_status')  
        filters_user = args.get('user')

        logger.debug(f"args = {args}")

        if order_id:
            order = await database_service.get_by_id('order_request', 'ID_order', order_id)
            payment = await database_service.get_by_id('payments', 'ID_order', order_id)
            text_message = admin_service.generate_message(order['ID_order'], order['ID_user'], order['ID_worker'], order['subject'], order['type_work'], order['order_details'], payment['price'], order['status'], payment['status'])

            await message.answer(text=text_message, parse_mode='HTML')
        elif show_all:
            pass
        elif filters_order_status:
            pass
        elif filters_pay_status:
            pass
        elif filters_user:
            pass



    except Exception as e:
        logger.error(f"eroor: {e}")