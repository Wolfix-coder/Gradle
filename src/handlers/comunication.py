import aiosqlite
from aiogram import Router, types, F

from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from services.admin_service import AdminService
from services.database_service import DatabaseService
from states.user_states import UserState
from utils.decorators import require_admin
from utils.logging import get_logger

comunication_router = Router()

logger = get_logger("handlers/communication")

admin_service = AdminService()
database_service = DatabaseService()

# ==========================================
# АДМІН: Команда /send_message
# ==========================================

@comunication_router.message(Command("send_message"))
@require_admin
async def send_message(message: Message, state: FSMContext):
    """Відправлення повідомлення користувачу"""
    try:
        # Парсинг команди
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

        # Визначення user_id
        user_id = None
        if args.get('id') and args.get('link'):
            await message.answer(text=(
                f"<b>Помилка!</b>\n\n"
                f"Вкажіть або <code>-id</code>, або <code>-link</code>, але не обидва.\n"
            ), parse_mode="HTML")
            return
        elif args.get('id'):
            user_id = args.get('id')
        elif args.get('link'):
            user_link = admin_service.parse_at_tags(args.get('link'))
            user_data = await database_service.get_by_id('user_data', 'user_link', user_link)
            if user_data:
                user_id = user_data['ID']
            else:
                await message.answer("❌ Користувача з таким username не знайдено!")
                return
        else:
            await message.answer(text=(
                f"<b>Помилка!</b>\n\n"
                f"Необхідно вказати або <code>-id</code>, або <code>-link</code>.\n"
            ), parse_mode="HTML")
            return

        # Перевірка тексту
        if not args.get('text'):
            await message.answer(text=(
                f"<b>Помилка!</b>\n\n"
                f"Необхідно вказати <code>-text</code> з текстом повідомлення.\n"
            ), parse_mode="HTML")
            return

        text_message = args.get('text')
        admin_id = message.from_user.id

        # Створення кнопки для відповіді
        builder = InlineKeyboardBuilder()
        builder.button(text="↩️ Відповісти", callback_data=f"reply_user:{user_id}:{admin_id}")

        # Отримання даних адміна
        admin_data = await database_service.get_by_id('user_data', 'ID', admin_id)
        admin_username = admin_data.get('user_link', 'Адміністратор') if admin_data else 'Адміністратор'

        # Відправка повідомлення користувачу
        await message.bot.send_message(
            chat_id=user_id, 
            text=f"📩 Адміністратор @{admin_username} надіслав вам повідомлення:"
        )
        await message.bot.send_message(
            chat_id=user_id, 
            text=text_message, 
            parse_mode='HTML', 
            reply_markup=builder.as_markup()
        )

        # Підтвердження адміну
        await message.answer("✅ Повідомлення успішно відправлено!")
        
        logger.info(f"Адмін {admin_id} надіслав повідомлення користувачу {user_id}")

    except Exception as e:
        await message.answer("❌ Виникла помилка при надсиланні повідомлення. Спробуйте пізніше.")
        logger.exception(f"Помилка команди /send_message: ")

    
# ==========================================
# КОРИСТУВАЧ: Відповідь адміну (Callback)
# ==========================================
    
@comunication_router.callback_query(F.data.startswith("reply_user:"))
async def reply_message_from_user(callback: CallbackQuery, state: FSMContext):
    """Callback коли користувач натискає кнопку 'Відповісти'"""
    try:
        await callback.answer()

        # Парсинг даних з callback
        parts = callback.data.split(':')
        if len(parts) < 3:
            await callback.message.answer("❌ Помилка: неправильний формат даних")
            return
            
        user_id = callback.from_user.id
        admin_id = parts[2]

        # Встановлюємо стан очікування повідомлення
        await state.set_state(UserState.waiting_for_reply_message_user)
        await state.update_data(user_id=user_id, admin_id=admin_id)

        await callback.message.answer(
            "📝 Надішліть відповідь адміністратору в наступному повідомленні.\n\n"
            "Просто напишіть текст і відправте."
        )
        
        logger.debug(f"Користувач {user_id} почав відповідь адміну {admin_id}")
        
    except Exception as e:
        await callback.answer("❌ Ой! Виникла помилка. Спробуйте пізніше.", show_alert=True)
        logger.exception(f"Помилка в reply_message_from_user: ")


# ==========================================
# КОРИСТУВАЧ: Відправка повідомлення (Message Handler)
# ==========================================

@comunication_router.message(UserState.waiting_for_reply_message_user)
async def send_reply_to_admin(message: Message, state: FSMContext):
    """Handler для отримання текстового повідомлення від користувача"""
    try:
        # Отримуємо збережені дані
        data = await state.get_data()
        user_id = data.get("user_id")
        admin_id = data.get("admin_id")

        if not user_id or not admin_id:
            await message.answer("❌ Помилка: дані втрачено. Почніть спочатку.")
            await state.clear()
            return

        message_text = message.text

        # Створення кнопки для зворотної відповіді
        builder = InlineKeyboardBuilder()
        builder.button(text="↩️ Відповісти", callback_data=f"reply_admin:{user_id}:{admin_id}")

        # Отримання даних користувача
        user_data = await database_service.get_by_id('user_data', 'ID', user_id)
        user_username = user_data.get('user_link', f'ID:{user_id}') if user_data else f'ID:{user_id}'

        # Відправка адміну
        await message.bot.send_message(
            chat_id=admin_id, 
            text=(
                f"📨 <b>Відповідь від користувача @{user_username}</b>\n\n"
                f"{message_text}"
            ),
            parse_mode="HTML", 
            reply_markup=builder.as_markup()
        )
        
        # Підтвердження користувачу
        await message.answer("✅ Ваше повідомлення успішно відправлено адміністратору!")
        
        logger.info(f"Користувач {user_id} надіслав відповідь адміну {admin_id}")

        # Очищення стану
        await state.clear()

    except Exception as e:
        await message.answer("❌ Виникла помилка при надсиланні повідомлення. Спробуйте пізніше.")
        logger.exception(f"Помилка в send_reply_to_admin: ")
        await state.clear()

    
# ==========================================
# АДМІН: Відповідь користувачу (Callback)
# ==========================================

@comunication_router.callback_query(F.data.startswith("reply_admin:"))
async def reply_message_from_admin(callback: CallbackQuery, state: FSMContext):
    """Callback коли адмін натискає кнопку 'Відповісти'"""
    try:
        await callback.answer()

        # Парсинг даних
        parts = callback.data.split(':')
        if len(parts) < 3:
            await callback.message.answer("❌ Помилка: неправильний формат даних")
            return

        admin_id = callback.from_user.id
        user_id = parts[1]

        # Встановлюємо стан
        await state.set_state(UserState.waiting_for_reply_message_admin)
        await state.update_data(user_id=user_id, admin_id=admin_id)

        await callback.message.answer(
            "📝 Надішліть відповідь користувачу в наступному повідомленні.\n\n"
            "Просто напишіть текст і відправте."
        )
        
        logger.debug(f"Адмін {admin_id} почав відповідь користувачу {user_id}")
        
    except Exception as e:
        await callback.answer("❌ Ой! Виникла помилка. Спробуйте пізніше.", show_alert=True)
        logger.exception(f"Помилка в reply_message_from_admin: ")


# ==========================================
# АДМІН: Відправка повідомлення (Message Handler)
# ==========================================

@comunication_router.message(UserState.waiting_for_reply_message_admin)
async def send_reply_to_user(message: Message, state: FSMContext):
    """Handler для отримання текстового повідомлення від адміна"""
    try:
        # Отримуємо збережені дані
        data = await state.get_data()
        user_id = data.get("user_id")
        admin_id = data.get("admin_id")

        if not user_id or not admin_id:
            await message.answer("❌ Помилка: дані втрачено. Почніть спочатку.")
            await state.clear()
            return

        message_text = message.text

        # Створення кнопки для відповіді
        builder = InlineKeyboardBuilder()
        builder.button(text="↩️ Відповісти", callback_data=f"reply_user:{user_id}:{admin_id}")

        # Отримання даних адміна
        admin_data = await database_service.get_by_id('user_data', 'ID', admin_id)
        admin_username = admin_data.get('user_link', 'Адміністратор') if admin_data else 'Адміністратор'

        # Відправка користувачу
        await message.bot.send_message(
            chat_id=user_id,
            text=(
                f"📩 <b>Відповідь від адміністратора @{admin_username}</b>\n\n"
                f"{message_text}"
            ),
            parse_mode="HTML",
            reply_markup=builder.as_markup()
        )
        
        # Підтвердження адміну
        await message.answer("✅ Ваше повідомлення успішно відправлено користувачу!")
        
        logger.info(f"Адмін {admin_id} надіслав відповідь користувачу {user_id}")

        # Очищення стану
        await state.clear()

    except Exception as e:
        await message.answer("❌ Виникла помилка при надсиланні повідомлення. Спробуйте пізніше.")
        logger.exception(f"Помилка в send_reply_to_user: ")
        await state.clear()