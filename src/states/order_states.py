from aiogram.fsm.state import State, StatesGroup

class OrderStates(StatesGroup):
    AWAITING_WORK = State()
    AWAITING_CORRECT = State()
    AWAITING_FEEDBACK = State()
    
    waiting_for_type = State()
    waiting_for_details = State()
    waiting_for_comment = State()