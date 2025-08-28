from aiogram.fsm.state import State, StatesGroup

class PaymentStates(StatesGroup):
    AWAITING_PRICE = State()
