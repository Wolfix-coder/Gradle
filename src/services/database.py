# services/database.py
import aiosqlite
import logging
from typing import AsyncContextManager
from config import Config

class DBConnection:
    _instance = None
    _connection = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, db_path: str = Config.DATABASE_PATH):
        if not hasattr(self, 'initialized'):
            self.db_path = db_path
            self.logger = logging.getLogger(__name__)
            self.initialized = True

    async def get_connection(self) -> aiosqlite.Connection:
        if self._connection is None:
            try:
                self._connection = await aiosqlite.connect(self.db_path)
                self.logger.info("Database connection established")
            except Exception as e:
                self.logger.error(f"Database connection error: {e}")
                raise
        return self._connection

    async def close(self):
        if self._connection is not None:
            await self._connection.close()
            self._connection = None
            self.logger.info("Database connection closed")

    async def create_tables(self):
        try:
            conn = await self.get_connection()
            
            # Таблиця замовлень
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS request_order (
                    ID_order TEXT PRIMARY KEY,
                    ID_user INTEGER,
                    ID_worker INTEGER,
                    subject TEXT,
                    type_work TEXT,
                    order_details TEXT,
                    status INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP,
                    updated_at TIMESTAMP,
                    total_price REAL DEFAULT 0,
                    paid_amount REAL DEFAULT 0,
                    FOREIGN KEY (ID_user) REFERENCES users (ID),
                    FOREIGN KEY (ID_worker) REFERENCES users (ID)
                )
            """)

            # Таблиця користувачів
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    ID INTEGER PRIMARY KEY,
                    user_name TEXT,
                    user_link TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    role TEXT DEFAULT 'user'
                )
            """)

            # Таблиця платежів
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS payments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ID_order TEXT,
                    amount REAL,
                    status TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (ID_order) REFERENCES request_order (ID_order)
                )
            """)

            # Індекси
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_worker_status ON request_order (ID_worker, status)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_status ON request_order (status)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_worker_completed ON request_order (ID_worker, status, completed_at)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_user_role ON users (role)")

            await conn.commit()
            self.logger.info("Database tables created successfully")
            
        except Exception as e:
            self.logger.error(f"Error creating database tables: {e}")
            raise
logger = logging.getLogger(__name__)

class DatabaseService:
    @staticmethod
    async def create_tables():
        try:
            async with aiosqlite.connect(Config.DATABASE_PATH) as db:
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        ID INTEGER PRIMARY KEY,
                        user_name TEXT NOT NULL,
                        user_link TEXT,
                        real_full_name TEXT NOT NULL,
                        for_father TEXT NOT NULL,
                        education TEXT NOT NULL,
                        course TEXT NOT NULL,
                        edu_group TEXT NOT NULL,
                        phone_number TEXT NOT NULL,
                        language_code TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                await db.commit()
                
            async with aiosqlite.connect(Config.DATABASE_PATH) as db:
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS request_order (
                        ID_order TEXT PRIMARY KEY,
                        ID_user INTEGER NOT NULL,
                        ID_worker INTEGER,
                        subject TEXT NOT NULL,
                        type_work TEXT NOT NULL,
                        order_details TEXT NOT NULL,
                        status INTEGER NOT NULL,
                        created_at TEXT NOT NULL,
                        taken_at TEXT,
                        completed_at TEXT,
                        FOREIGN KEY (ID_user) REFERENCES users(ID)
                    )
                """)
                await db.commit()
        except aiosqlite.Error as e:
            logger.error(f"Database error during table creation: {e}")
            raise

    @staticmethod
    async def check_user_exists(user_id: int) -> bool:
        try:
            async with aiosqlite.connect(Config.DATABASE_PATH) as db:
                async with db.execute("SELECT 1 FROM users WHERE ID = ?", (user_id,)) as cursor:
                    return bool(await cursor.fetchone())
        except aiosqlite.Error as e:
            logger.error(f"Database error while checking user: {e}")
            return False

# Функція для створення таблиць (для сумісності)
async def create_tables():
    db = DBConnection()
    await db.create_tables()

# Функція для ініціалізації БД
async def init_db():
    db = DBConnection()
    await db.create_tables()
    return db

# Експортуємо все необхідне
__all__ = ['DBConnection', 'create_tables', 'init_db']