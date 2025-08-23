import asyncio
import signal
from contextlib import suppress
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

# Абсолютні імпорти роутерів
from handlers.admin import admin_router
from handlers.basic import basic_router
from handlers.orders import user_orders_router, admin_orders_router
from handlers.payments import user_payments_router, admin_payments_router
from handlers.statistics import statistics_router
from handlers.users import user_router

from services.database_service import DBCreator
from utils.logging import logger
from config import Config

class BotRunner:
    def __init__(self):
        self.shutdown_event = asyncio.Event()
        self.bot = None
        self.dp = None
        
    def handle_shutdown(self, signum, frame):
        """Обробник сигналу завершення."""
        logger.info("Отримано сигнал завершення роботи...")
        self.shutdown_event.set()

    async def register_routers(self):
        """Реєстрація всіх роутерів."""
        # Адмін роутери
        self.dp.include_router(admin_router)
        self.dp.include_router(admin_orders_router)
        self.dp.include_router(admin_payments_router)
        self.dp.include_router(statistics_router)
        
        # Користувацькі роутери
        self.dp.include_router(basic_router)
        self.dp.include_router(user_orders_router)
        self.dp.include_router(user_payments_router)
        self.dp.include_router(user_router)
        
        logger.info("Всі роутери успішно зареєстровані")

    async def init_services(self):
        """Ініціалізація всіх сервісів."""
        try:
            if await DBCreator.create_tables() == True:
                logger.info("Таблиці бази даних успішно створені")
            else:
                logger.error(f"Помилка при створені створені БД")
        except Exception as e:
            logger.error(f"Помилка ініціалізації сервісів: {e}")
            raise

    async def start(self):
        """Запуск бота."""
        try:
            logger.info("Бот запускається...")
            
            # Налаштовуємо обробники сигналів
            signal.signal(signal.SIGINT, self.handle_shutdown)
            signal.signal(signal.SIGTERM, self.handle_shutdown)
            
            # Ініціалізуємо бота та диспетчер
            self.bot = Bot(
                token=Config.BOT_TOKEN,
                default=DefaultBotProperties(parse_mode=ParseMode.HTML)
            )
            self.dp = Dispatcher()

            # Ініціалізуємо сервіси
            await self.init_services()
            
            # Реєструємо роутери
            await self.register_routers()
            
            logger.info('Бот активний')

            # Запускаємо поллінг
            polling_task = asyncio.create_task(self.dp.start_polling(self.bot))
            
            # Очікуємо сигнал завершення
            await self.shutdown_event.wait()
            
            # Скасовуємо поллінг
            polling_task.cancel()
            
            with suppress(asyncio.CancelledError):
                await polling_task
                
        except Exception as e:
            logger.error(f"Помилка запуску бота: {e}")
            raise
        finally:
            if self.bot:
                await self.bot.session.close()
                logger.info("Бот успішно зупинений")

def run_bot():
    """Головна функція запуску бота."""
    runner = BotRunner()
    try:
        asyncio.run(runner.start())
    except KeyboardInterrupt:
        logger.info("Бот зупинений користувачем")
    except Exception as e:
        logger.error(f"Критична помилка: {e}")

if __name__ == "__main__":
    run_bot()