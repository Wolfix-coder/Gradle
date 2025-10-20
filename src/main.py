import asyncio
from aiohttp import web
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from handlers.admin import admin_router
from handlers.basic import basic_router
from handlers.comunication import comunication_router
from handlers.orders import user_orders_router, admin_orders_router
from handlers.payments import user_payments_router, admin_payments_router
from handlers.statistics import statistics_router
from handlers.users import user_router

from services.database_service import DBCreator
from utils.logging import logger
from config import Config


class BotRunner:
    def __init__(self):
        self.bot = Bot(
            token=Config.BOT_TOKEN,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML)
        )
        self.dp = Dispatcher()
        self.app = web.Application()

        # Webhook URL (твій домен Railway)
        self.WEBHOOK_PATH = f"/webhook/{Config.BOT_TOKEN}"
        self.WEBHOOK_URL = f"{Config.WEBHOOK_BASE_URL}{self.WEBHOOK_PATH}"

    async def init_services(self):
        """Ініціалізація бази даних та інших сервісів."""
        try:
            if await DBCreator.create_tables():
                logger.info("Таблиці бази даних успішно створені")
            else:
                logger.error("Помилка при створенні БД")
        except Exception as e:
            logger.error(f"Помилка ініціалізації сервісів: {e}")
            raise

    async def register_routers(self):
        """Реєстрація роутерів."""
        # Адмінські
        self.dp.include_router(admin_router)
        self.dp.include_router(admin_orders_router)
        self.dp.include_router(admin_payments_router)
        self.dp.include_router(statistics_router)
        self.dp.include_router(comunication_router)
        # Користувацькі
        self.dp.include_router(basic_router)
        self.dp.include_router(user_orders_router)
        self.dp.include_router(user_payments_router)
        self.dp.include_router(user_router)

        logger.info("Всі роутери успішно зареєстровані")

    async def on_startup(self, app: web.Application):
        """Подія запуску — встановлює webhook."""
        await self.bot.set_webhook(self.WEBHOOK_URL)
        await self.init_services()
        await self.register_routers()
        logger.info(f"Webhook встановлено: {self.WEBHOOK_URL}")

    async def on_shutdown(self, app: web.Application):
        """Подія завершення роботи — видаляє webhook."""
        await self.bot.delete_webhook()
        await self.bot.session.close()
        logger.info("Webhook видалено, бот зупинений")

    async def handle_webhook(self, request: web.Request):
        """Обробка вхідних апдейтів від Telegram."""
        data = await request.json()
        update = types.Update(**data)
        await self.dp.feed_update(self.bot, update)
        return web.Response()

    def run(self):
        """Запуск aiohttp-сервера."""
        self.app.router.add_post(self.WEBHOOK_PATH, self.handle_webhook)
        self.app.on_startup.append(self.on_startup)
        self.app.on_shutdown.append(self.on_shutdown)

        logger.info("Бот запускається у режимі webhook (serverless Railway)...")
        web.run_app(self.app, host="0.0.0.0", port=8080)


if __name__ == "__main__":
    runner = BotRunner()
    runner.run()
