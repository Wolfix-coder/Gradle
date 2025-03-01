from aiogram.fsm.state import State, StatesGroup

class UserState(StatesGroup):
    waiting_for_real_full_name = State()
    waiting_for_patronymic = State()
    waiting_for_education_place = State()
    waiting_for_course = State()
    waiting_for_group = State()

# class UserData(StatesGroup):
    
#     """
#     Клас для зберігання станів користувача
#     """
#     # Стани для реєстрації
#     waiting_for_real_full_name = State()        # Реальне ім'я юзера
#     waiting_for_patronymic = State()            # Реальне побатькові
#     waiting_for_education_place = State()       # Навчальний заклад
#     waiting_for_course = State()                # Курс
#     waiting_for_group = State()                 # Група
    
#     # Стани для замовлення
#     selecting_product = State()       # Вибір продукту
#     entering_quantity = State()       # Введення кількості
#     confirming_order = State()        # Підтвердження замовлення
    
#     # Стани для зворотного зв'язку
#     writing_feedback = State()        # Написання відгуку
    
#     # Додаткові стани
#     editing_profile = State()         # Редагування профілю
#     support_chat = State()
