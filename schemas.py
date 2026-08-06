from pydantic import BaseModel
from typing import Optional, List, Dict, Any

class UserBase(BaseModel):
    username: str

class UserCreate(UserBase):
    password: str
    role: Optional[str] = "USER"
    forex_enabled: Optional[int] = 0

class UserUpdatePassword(BaseModel):
    new_password: str

class UserUpdateForex(BaseModel):
    forex_enabled: int

class User(UserBase):
    id: int
    role: str
    forex_enabled: int
    expiration_date: Optional[str] = None
    last_payment_date: Optional[str] = None
    subscription_type: Optional[str] = None
    is_suspended: Optional[int] = 0

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
