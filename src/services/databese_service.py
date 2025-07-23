import aiosqlite

from typing import Optional, Dict, Any, List
from utils.logging import logger
from utils.validators import _validate_table_column

from config import Config

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
           _validate_table_column(table, column)
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
            _validate_table_column(table, column)
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