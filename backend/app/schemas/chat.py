from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class ThreadCreate(BaseModel):
    title: Optional[str] = "New conversation"


class ThreadResponse(BaseModel):
    id: str
    user_id: int
    title: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MessageResponse(BaseModel):
    id: str
    thread_id: str
    role: str
    content: str
    message_type: str
    created_at: datetime

    class Config:
        from_attributes = True


class ChatRequest(BaseModel):
    thread_id: Optional[str] = None
    message: str = Field(..., min_length=1)
    stream: bool = False


class ChatResponse(BaseModel):
    thread_id: str
    message: str
    title: Optional[str] = None


class MemoryResponse(BaseModel):
    id: str
    user_id: int
    memory_key: str
    memory_value: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
