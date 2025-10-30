from functools import wraps
from aiogram.types import Message
from config import Config  

def require_admin(func):
    @wraps(func)
    async def wrapper(message: Message, *args, **kwargs):
        if message.from_user.id in Config.ADMIN_IDS:  # Використовуємо Config.ADMIN_IDS
            return await func(message, *args, **kwargs)
        else:
            await message.answer("У вас немає прав для виконання цієї команди.")
            return False
    return wrapper