import aiosqlite

from typing import Optional, Dict, Any, List

from model.order import OrderStatus
from utils.logging import logger
from utils.validators import _validate_table_column

from config import Config

class DBCreator:
    @staticmethod
    async def create_tables() -> bool:
        try:
            async with aiosqlite.connect(Config.DATABASE_PATH) as db:
                try:
                    await db.execute("""
                        CREATE TABLE IF NOT EXISTS user_data (
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
                    logger.error(f"Error create table user_data: {e}")

            try:
                async with aiosqlite.connect(Config.DATABASE_PATH) as db:
                    await db.execute("""
                        CREATE TABLE IF NOT EXISTS order_request (
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
                            FOREIGN KEY (ID_user) REFERENCES user_data(ID)
                        )
                    """)
                    await db.commit()
            except aiosqlite.Error as e:
                    logger.error(f"Error create table order_request: {e}")

            try:
                # Таблиця платежів
                async with aiosqlite.connect(Config.DATABASE_PATH) as db:
                    await db.execute("""
                    CREATE TABLE IF NOT EXISTS payments (
                        id_operation INTEGER PRIMARY KEY AUTOINCREMENT,
                        ID_order TEXT,
                        client_id TEXT,
                        status TEXT,
                        price REAL,
                        paid REAL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        paid_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    """)
                
                    await db.commit()
                return True
            except aiosqlite.Error as e:
                    logger.error(f"Error create table payments: {e}")
        
        except aiosqlite.Error as e:
            logger.error(f"Database error during table creation: {e}")
            raise

class DatabaseService:
    def __init__(self):
        self.db_path = Config.DATABASE_PATH

    async def _get_db_connection(self):
        try:
            db = await aiosqlite.connect(self.db_path)
            db.row_factory = aiosqlite.Row # Для повернення інформації у вигляді (id = '1234', name = 'John', ...)
            return db
        except Exception as e:
            logger.error(f"Помилка підключення до БД: {e}")
            raise
    
    async def get_by_id(self, table: str, column: str, id_value: Any) -> Optional[Dict]:
        """
        Отримання одного запису по ID

        Args:
            table: str - назва таблиці (наприклад 'payments')
            column: str - назва поля ID (наприклад 'ID_worker')
            id_value: Any - значення ID (може бути str "001234" або int 123)
        
        Return:
            Optional[Dict] - словник зі всіма знайденими значеннями, або None якщо не знайдено
        """
        db = None

        try:
           db = await self._get_db_connection()
           _validate_table_column(table, column) # Валідація table and column
           async with db.execute(f"SELECT * FROM {table} WHERE {column} = ?", (id_value,)) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None
        except aiosqlite.Error as e:
            logger.error(f"Помилка отримання данних з бд: {e}")
            raise
        except ValueError as e:
            logger.error(f"Помилка валідації: {e}")
            raise
        finally:
            if db:
                await db.close()
    
    async def get_all_by_field(self, table: str, column: str, field_value: Any) -> List[Dict]:
        """
        Отримання всіх записів по фільтру (field_value)

        Args:
            table: str - назва таблиці (наприклад 'orders')
            column: str - назва поля ID (наприклад 'status')
            field_value - значення фільтру за яким будуть відображатися знайдені рядки (наприклад 'pending')

        Return:
            List[Dict] - список усіх знайдених збігів, або [] якщо нічого не знайдено
        """
        db = None

        try:
            db = await self._get_db_connection()
            _validate_table_column(table, column) # Валідація table and column
            async with db.execute(f"SELECT * FROM {table} WHERE {column} = ?", (field_value,)) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

        except aiosqlite.Error as e:
            logger.error(f"Помилка отримання данних з бд (get_all_by_field()): {e}")
            raise
        except ValueError as e:
            logger.error(f"Помилка валідації: {e}")
            raise
        finally:
            if db:
                await db.close()
    
    async def get_worker_statistics(self, worker_id: int) -> Dict:
        """
        Отримує статистику для конкретного працівника.
        
        Args:
            worker_id (int): ID працівника
            
        Returns:
            Dict: Словник зі статистикою, що містить:
                - total_completed: загальна кількість виконаних замовлень
                - active_orders: кількість активних замовлень
                - top_subjects: список кортежів (предмет, кількість замовлень)
        """
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                
                # Отримуємо кількість виконаних замовлень
                async with db.execute("""
                    SELECT COUNT(*) as count 
                    FROM order_request 
                    WHERE ID_worker = ? AND status = ?
                """, (worker_id, OrderStatus.COMPLETED.value)) as cursor:
                    completed = await cursor.fetchone()
                    total_completed = completed['count']

                # Отримуємо кількість активних замовлень
                async with db.execute("""
                    SELECT COUNT(*) as count 
                    FROM order_request
                    WHERE ID_worker = ? AND status = ?
                """, (worker_id, OrderStatus.IN_PROGRESS.value)) as cursor:
                    active = await cursor.fetchone()
                    active_orders = active['count']

                # Отримуємо топ предметів
                async with db.execute("""
                    SELECT subject, COUNT(*) as count 
                    FROM order_request
                    WHERE ID_worker = ? AND status = ?
                    GROUP BY subject 
                    ORDER BY count DESC 
                    LIMIT 5
                """, (worker_id, OrderStatus.COMPLETED.value)) as cursor:
                    subjects = await cursor.fetchall()
                    top_subjects = [(row['subject'], row['count']) for row in subjects]

                return {
                    'total_completed': total_completed,
                    'active_orders': active_orders,
                    'top_subjects': top_subjects
                }
                
        except Exception as e:
            logger.error(f"Помилка при отриманні статистики для працівника {worker_id}: {e}")
            raise