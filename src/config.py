import os
from dotenv import load_dotenv

# Завантажуємо змінні середовища з .env файлу
load_dotenv()

class Config:
    # Токен бота
    BOT_TOKEN = os.getenv("BOT_TOKEN")

    WEBHOOK_BASE_URL = os.getenv("WEBHOOK_BASE_URL")
    
    # ID адміністраторів (можна додати декілька)
    ADMIN_IDS = [int(id) for id in os.getenv("ADMIN_IDS", "").split(",") if id]

    # ID адмін каналу
    ADMIN_CHANNEL_ID = os.getenv("ADMIN_CHANNEL_ID")
    
    # Налаштування бази даних
    DATABASE_PATH = os.getenv("DATABASE_PATH", "database.sqlite")
    
    # Налаштування платежів (якщо потрібно)
    PAYMENT_TOKEN = os.getenv("PAYMENT_TOKEN")
    
    # Інші налаштування
    DEBUG = os.getenv("DEBUG", "False").lower() == "true"

    # Посилання на чат допомоги
    support_url = "https://t.me/Gradle_support_bot"

    MAX_COMMENT_LENGTH = 800
    
    @classmethod
    def validate(cls):
        """Перевірка наявності всіх необхідних налаштувань"""
        if not cls.BOT_TOKEN:
            raise ValueError("BOT_TOKEN не налаштовано")
        
        if not cls.ADMIN_IDS:
            raise ValueError("ADMIN_IDS не налаштовано")

# Перевіряємо конфігурацію при імпорті
Config.validate()