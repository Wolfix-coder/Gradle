import aiosqlite
from typing import Optional

from model.user import UserModel
from model.user import User
from services.database_service import DatabaseService
from utils.logging import get_logger

logger = get_logger("services/user_service")

class UserService:
    def __init__(self):
        self.db = DatabaseService()

    async def get_user(self, user_id: int) -> UserModel:
        try:
            async with self.db._get_db_connection() as conn:
                query = "SELECT * FROM users WHERE ID = ?"
                async with conn.execute(query, (user_id,)) as cursor:
                    user_data = await cursor.fetchone()
                    
                if user_data:
                    return UserModel(
                        id=user_data[0],
                        username=user_data[1],
                        user_link=user_data[2],
                        created_at=user_data[3]
                    )
                return None
                
        except Exception as e:
            logger.exception(f"Error getting user: ")
            raise

    async def create_user(self, user: UserModel) -> bool:
        try:
            async with self.db._get_db_connection() as conn:
                query = """
                    INSERT INTO users (ID, user_name, user_link, created_at)
                    VALUES (?, ?, ?, ?)
                """
                await conn.execute(query, (
                    user.id,
                    user.username,
                    user.user_link,
                    user.created_at
                ))
                await conn.commit()
                return True
                
        except Exception as e:
            logger.exception(f"Error creating user: ")
            raise

    @staticmethod
    async def create_user(user: User) -> bool:
        try:
            async with aiosqlite.connect("users.db") as db:
                await db.execute(
                    '''INSERT INTO users (
                        ID, user_name, user_link, real_full_name, for_father,
                        education, course, edu_group, phone_number, language_code
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                    (
                        user.id,
                        user.user_name,
                        user.user_link,
                        user.real_full_name,
                        user.for_father,
                        user.education,
                        user.course,
                        user.edu_group,
                        user.phone_number,
                        user.language_code
                    )
                )
                await db.commit()
                return True
        except aiosqlite.Error as e:
            logger.exception(f"Database error while creating user: ")
            return False

    @staticmethod
    async def get_user(user_id: int) -> Optional[User]:
        try:
            async with aiosqlite.connect("users.db") as db:
                async with db.execute(
                    "SELECT * FROM users WHERE ID = ?",
                    (user_id,)
                ) as cursor:
                    if row := await cursor.fetchone():
                        return User(
                            id=row[0],
                            user_name=row[1],
                            user_link=row[2],
                            real_full_name=row[3],
                            for_father=row[4],
                            education=row[5],
                            course=row[6],
                            edu_group=row[7],
                            phone_number=row[8],
                            language_code=row[9],
                            created_at=row[10]
                        )
            return None
        except aiosqlite.Error as e:
            logger.exception(f"Database error while getting user: ")
            return None