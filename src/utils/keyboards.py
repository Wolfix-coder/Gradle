from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder


def get_admin_keyboard() -> InlineKeyboardBuilder:
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="📋 Нові замовлення", callback_data="new_orders")
    keyboard.button(text="📋 Мої замовлення", callback_data="my_orders")
    keyboard.button(text="📊 Статистика", callback_data="my_statistics")
    keyboard.adjust(1)
    return keyboard

def get_user_pay_keyboard() -> InlineKeyboardBuilder:
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="Не оплачені замовлення", callback_data="unpaid_order")
    keyboard.adjust(1)
    return keyboard

def get_worker_order_keyboard(order_id: str) -> InlineKeyboardBuilder:
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="📤 Відправити роботу", callback_data=f"send_work_{order_id}")
    keyboard.adjust(1)
    return keyboard

def subject_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    subjects = [
        ("Біологія", "biology"),
        ("Всесвітня історія", "world_history"),
        ("Географія", "geography"),
        ("Іноземна мова", "eng_language"),
        ("Інформатика", "computer_science"),
        ("Історія України", "ua_history"),
        ("Зарубіжна література", "foreign_literature"),
        ("Захист України", "defense_ua"),
        ("Математика", "maths"),
        ("Українська література", "ua_literature"),
        ("Українська мова", "ua_language"),
        ("Хімія", "chemistry"),
        ("Фізика", "physics"),
        ("Фізична культура", "physical_culture"),
        ("Спец. урок", "special_lesson")
    ]
    for text, callback_data in subjects:
        builder.button(text=text, callback_data=callback_data)
    builder.adjust(1)
    return builder.as_markup()

def type_work_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for i in range(1, 9):
        builder.button(text=str(i), callback_data=str(i))
    builder.adjust(2)
    return builder.as_markup()

def get_phone_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Надати номер телефону", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True
    )

def get_education_keyboard() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text="Олександрійський Політех"),
        KeyboardButton(text="Інше")
    )
    return builder.as_markup(resize_keyboard=True)

def get_course_keyboard() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.row(*[KeyboardButton(text=str(i)) for i in range(1, 5)])
    return builder.as_markup(resize_keyboard=True)