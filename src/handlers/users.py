import aiosqlite
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram.filters.callback_data import CallbackData
from aiogram.types.callback_query import CallbackQuery
from aiogram.types import CallbackQuery, Message, ReplyKeyboardMarkup, KeyboardButton, ContentType, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from services.database import DatabaseService
from states.user_states import UserState
from utils.validators import validate_input, validate_course
from utils.logging import logger
from text import support_url
from config import Config

# Константи
MAX_NAME_LENGTH = 50
MAX_COMMENT_LENGTH = 500
MAX_GROUP_LENGTH = 10
ALLOWED_COURSES = ['1', '2', '3', '4']

router = Router()

@router.message(Command("start"))
async def cmd_start(message: types.Message):
    try:
        phone_button = KeyboardButton(text="Надати номер телефону", request_contact=True)
        phone_keyboard = ReplyKeyboardMarkup(
            keyboard=[[phone_button]],
            resize_keyboard=True,
            one_time_keyboard=True
        )
        await message.answer(
            "Натисніть кнопку нижче, щоб надати номер телефону для майбутнього спілкування стосовно замовлення.",
            reply_markup=phone_keyboard
        )
    except Exception as e:
        logger.error(f"Error in start command: {e}")
        await message.answer("Виникла помилка. Спробуйте пізніше.")

@router.message(F.content_type == ContentType.CONTACT)
async def handle_contact(message: types.Message, state: FSMContext):
    try:
        contact = message.contact
        user = message.from_user

        if await DatabaseService.check_user_exists(user.id):
            help_markup = ReplyKeyboardBuilder()
            help_markup.row(types.KeyboardButton(text="Допомога"))
            await message.answer(
                f"Користувач @{user.username} вже є в базі даних.\n"
                f"Введіть команду /help, щоб переглянути список команд.", 
                reply_markup=help_markup.as_markup(resize_keyboard=True)
            )
            return

        await state.update_data(contact=contact, user=user)
        await message.answer("Будь ласка, введіть своє ім'я та по батькові.")
        await state.set_state(UserState.waiting_for_real_full_name)
    except Exception as e:
        logger.error(f"Error handling contact: {e}")
        await message.answer("Виникла помилка. Спробуйте пізніше.")

@router.message(UserState.waiting_for_real_full_name)
async def get_full_name(message: Message, state: FSMContext):
    name = validate_input(message.text, MAX_NAME_LENGTH)
    if not name:
        await message.answer(f"Некоректне ім'я. Спробуйте ще раз (максимум {MAX_NAME_LENGTH} символів)")
        return
    
    await state.update_data(full_name=name)
    await message.answer("Введіть своє прізвище.")
    await state.set_state(UserState.waiting_for_patronymic)

@router.message(UserState.waiting_for_patronymic)
async def get_patronymic(message: types.Message, state: FSMContext):
    patronymic = validate_input(message.text, MAX_NAME_LENGTH)
    if not patronymic:
        await message.answer(f"Некоректне по батькові. Спробуйте ще раз (максимум {MAX_NAME_LENGTH} символів)")
        return

    await state.update_data(patronymic=patronymic)
    education_markup = ReplyKeyboardBuilder()
    education_markup.row(
        types.KeyboardButton(text="Олександрійський Політех"),
        types.KeyboardButton(text="Інше")
    )
    await message.answer(
        "Виберіть ваше місце навчання.", 
        reply_markup=education_markup.as_markup(resize_keyboard=True)
    )
    await state.set_state(UserState.waiting_for_education_place)

@router.message(UserState.waiting_for_education_place)
async def get_education_place(message: types.Message, state: FSMContext):
    if message.text == "Інше":
        education_markup = ReplyKeyboardBuilder()
        education_markup.row(
            types.KeyboardButton(text="Олександрійський Політех"),
            types.KeyboardButton(text="Інше")
        )
        education_markup.row(
            types.KeyboardButton(text="Повернутися до вибору закладу")
        )
        await message.answer(
            "Ви вибрали 'Інше'. Ви можете:\n"
            "1. Звернутися до підтримки\n"
            "2. Повернутися до вибору навчального закладу",
            reply_markup=education_markup.as_markup(resize_keyboard=True)
        )
        builder = InlineKeyboardBuilder()
        builder.add(types.InlineKeyboardButton(
            text="Підтримка",
            url=support_url
        ))
        await message.answer(
            "Якщо в списку немає вашого закладу освіти, будь ласка, зверніться до нас 👇",
            reply_markup=builder.as_markup()
        )
        return
    
    elif message.text == "Повернутися до вибору закладу":
        education_markup = ReplyKeyboardBuilder()
        education_markup.row(
            types.KeyboardButton(text="Олександрійський Політех"),
            types.KeyboardButton(text="Інше")
        )
        await message.answer(
            "Виберіть ваше місце навчання:", 
            reply_markup=education_markup.as_markup(resize_keyboard=True)
        )
        return

    elif message.text == "Олександрійський Політех":
        await state.update_data(education_place=message.text)
        course_markup = ReplyKeyboardBuilder()
        course_markup.row(
            *[types.KeyboardButton(text=str(i)) for i in range(1, 5)]
        )
        await message.answer(
            "Виберіть курс на якому ви навчаєтесь:",
            reply_markup=course_markup.as_markup(resize_keyboard=True)
        )
        await state.set_state(UserState.waiting_for_course)
    
    else:
        education_markup = ReplyKeyboardBuilder()
        education_markup.row(
            types.KeyboardButton(text="Олександрійський Політех"),
            types.KeyboardButton(text="Інше")
        )
        await message.answer(
            "Будь ласка, використовуйте кнопки для вибору навчального закладу:", 
            reply_markup=education_markup.as_markup(resize_keyboard=True)
        )

@router.message(UserState.waiting_for_course)
async def get_course(message: types.Message, state: FSMContext):
    if not validate_course(message.text):
        await message.answer("Невірний курс. Будь ласка, виберіть курс зі списку.")
        return

    await state.update_data(course=message.text)
    
    groups = {
        "1": ["ПК-241", "ПК-242", "КС-241", "ОМ-241", "РА-241", "РА-242", "АВ-241", "АП-241"],
        "2": ["ПК-231", "ПК-232", "КС-231", "ОМ-231", "РА-231", "РА-232", "АВ-231", "АП-231"],
        "3": ["ПК-221", "ПК-222", "КС-221", "ОМ-221", "РА-221", "РА-222", "АВ-221", "АП-221"],
        "4": ["ПК-211", "ПК-212", "КС-211", "ОМ-211", "РА-211", "РА-212", "АВ-211", "АП-211"]
    }
    
    group_markup = ReplyKeyboardBuilder()
    current_groups = groups[message.text]
    for i in range(0, len(current_groups), 4):
        group_markup.row(*[types.KeyboardButton(text=group) for group in current_groups[i:i+4]])
    
    await message.answer(
        "Виберіть свою групу.",
        reply_markup=group_markup.as_markup(resize_keyboard=True)
    )
    await state.set_state(UserState.waiting_for_group)

@router.message(UserState.waiting_for_group)
async def get_group(message: Message, state: FSMContext):
    try:
        group = validate_input(message.text, MAX_GROUP_LENGTH)
        if not group:
            await message.answer(f"Некоректна група. Спробуйте ще раз (максимум {MAX_GROUP_LENGTH} символів)")
            return

        user_data = await state.get_data()
        user = message.from_user
        
        async with aiosqlite.connect(Config.DATABASE_PATH) as db:
            await db.execute(
                '''INSERT INTO users (
                    ID, user_name, user_link, real_full_name, for_father,
                    education, course, edu_group, phone_number, language_code
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (
                    user.id,
                    f"{user.first_name} {user.last_name or ''}".strip() or user.username or "Unknown",
                    user.username,
                    user_data['full_name'],
                    user_data['patronymic'],
                    user_data['education_place'],
                    user_data['course'],
                    group,
                    user_data['contact'].phone_number,
                    user_data['user'].language_code
                )
            )
            await db.commit()
        
        await message.answer(
            "Ваші дані успішно збережено.",
            reply_markup=types.ReplyKeyboardRemove()
        )

        help_markup = ReplyKeyboardBuilder()
        help_markup.row(types.KeyboardButton(text="Допомога"))
        await message.answer(
            "Введіть команду /help або натисніть на кнопку \"Допомога\", щоб побачити список доступних команд:",
            reply_markup=help_markup.as_markup(resize_keyboard=True)
        )
        await state.clear()
        
    except aiosqlite.Error as e:
        logger.error(f"Database error while saving user data: {e}")
        await message.answer("Виникла помилка при збереженні даних. Спробуйте пізніше.")
    except Exception as e:
        logger.error(f"Unexpected error in get_group: {e}")
        await message.answer("Виникла непередбачена помилка. Спробуйте пізніше.")
