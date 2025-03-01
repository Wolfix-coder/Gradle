from pydantic import BaseModel
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

class UserModel(BaseModel):
    id: int
    username: str
    user_link: str
    created_at: datetime = datetime.now()

    class Config:
        from_attributes = True

@dataclass
class User:
    id: int
    user_name: str
    user_link: Optional[str]
    real_full_name: str
    for_father: str
    education: str
    course: str
    edu_group: str
    phone_number: str
    language_code: Optional[str]
    created_at: datetime = datetime.now()