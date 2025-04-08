from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional, Dict, Any

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

class RequestBase(BaseModel):
    method: Optional[str] = None
    url: Optional[str] = None
    status_code: Optional[int] = None

class Request(RequestBase):
    id: int
    string_response: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    request_origin_id: Optional[int] = None
    chrome_session_id: Optional[int] = None
    user_id: int

    class Config:
        from_attributes = True

class ChromeSessionBase(BaseModel):
    session_id: str
    proxy: Optional[str] = None

class ChromeSession(ChromeSessionBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    user_id: int

    class Config:
        from_attributes = True

class BrowserAction(BaseModel):
    action: str
    value: Optional[str] = None
    selector: Optional[str] = None

class TaskStatus(BaseModel):
    task_id: str
    status: str
    result: Optional[Dict[str, Any]] = None

