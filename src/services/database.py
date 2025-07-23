import aiosqlite

from utils.logging import logger
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

class DatabaseService:
    @staticmethod
    async def create_tables() -> bool:
        try:
            async with aiosqlite.connect(Config.DATABASE_PATH) as db:
                try:
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
                except aiosqlite.Error as e:
                    logger.error(f"Error create table users: {e}")

            try:
                async with aiosqlite.connect(Config.DATABASE_PATH) as db:
                    await db.execute("""
                        CREATE TABLE IF NOT EXISTS order (
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
                            updated_at TEXT,
                            FOREIGN KEY (ID_user) REFERENCES users(ID)
                        )
                    """)
                    await db.commit()
            except aiosqlite.Error as e:
                    logger.error(f"Error create table order: {e}")

            try:
                # Таблиця платежів
                async with aiosqlite.connect(Config.DATABASE_PATH) as db:
                    await db.execute("""
                    CREATE TABLE IF NOT EXISTS payments (
                        id_operation INTEGER PRIMARY KEY AUTOINCREMENT,
                        ID_order TEXT,
                        status TEXT,
                        price REAL,
                        paid REAL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        paid_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                return True
            except aiosqlite.Error as e:
                    logger.error(f"Error create table payments: {e}")
        
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