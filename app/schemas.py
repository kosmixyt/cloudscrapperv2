from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional

class UserBase(BaseModel):
    email: EmailStr
    full_name: str

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

class LoginData(BaseModel):
    email: EmailStr
    password: str

class AllowedOriginBase(BaseModel):
    origin: str

class AllowedOriginCreate(AllowedOriginBase):
    pass

class AllowedOrigin(AllowedOriginBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    owner_id: int
    disabled: bool = False

    class Config:
        from_attributes = True