from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command

from utils.decorators import require_admin
from utils.keyboards import get_admin_keyboard

import logging

admin_router = Router(name='admin')

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