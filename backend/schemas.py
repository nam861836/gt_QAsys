from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime
from models import DocumentType

class UserBase(BaseModel):
    email: EmailStr
    username: str

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

class ChatMessage(BaseModel):
    message: str
    chat_type: str = "chat"  # 'chat' or 'document_qa'

class ChatResponse(BaseModel):
    response: str
    chat_type: str

class ChatHistoryResponse(BaseModel):
    id: int
    message: str
    response: str
    chat_type: str
    created_at: datetime

    class Config:
        from_attributes = True

class DocumentBase(BaseModel):
    filename: str
    file_type: DocumentType

class DocumentCreate(DocumentBase):
    content: str

class DocumentResponse(DocumentBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

class WebSearchResult(BaseModel):
    title: str
    snippet: str
    url: str

class WeatherInfo(BaseModel):
    city: str
    temperature: float
    description: str
    humidity: int
    wind_speed: float 