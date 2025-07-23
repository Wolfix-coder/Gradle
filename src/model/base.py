from datetime import datetime
from pydantic import BaseModel, validator
from dataclasses import dataclass

class BaseDBModel(BaseModel):
    created_at: datetime = datetime.now()
    updated_at: datetime = datetime.now()
    
    @validator('updated_at', always=True)
    def set_updated_at(cls, v):
        return datetime.now()
    
@dataclass
class Model:
        # Info user
    ID: int
    user_name: str
    user_link: str
    real_full_name: str
    for_father: str
    education: str
    course: int
    edu_group: int