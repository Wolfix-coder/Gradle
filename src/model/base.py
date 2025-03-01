from datetime import datetime
from pydantic import BaseModel, validator

class BaseDBModel(BaseModel):
    created_at: datetime = datetime.now()
    updated_at: datetime = datetime.now()
    
    @validator('updated_at', always=True)
    def set_updated_at(cls, v):
        return datetime.now()