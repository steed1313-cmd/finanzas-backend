from pydantic import BaseModel
from typing import Optional, List, Dict, Any

class UserBase(BaseModel):
    username: str

class UserCreate(UserBase):
    password: str

class UserUpdatePassword(BaseModel):
    new_password: str

class User(UserBase):
    id: int
    role: str

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str
    user: User

class TokenData(BaseModel):
    username: Optional[str] = None

class MonthlyDataCreate(BaseModel):
    month_key: str
    data: str  # JSON string

class MonthlyData(MonthlyDataCreate):
    id: int
    user_id: int

    class Config:
        from_attributes = True

class MigrateData(BaseModel):
    local_storage_data: Dict[str, Any]
