from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from enum import Enum

class MessageType(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"

class SearchStage(str, Enum):
    SEARCHING = "searching"
    READING = "reading"
    WRITING = "writing"
    ERROR = "error"

class SearchInfo(BaseModel):
    stages: List[SearchStage] = []
    query: str = ""
    urls: List[str] = []
    error: Optional[str] = None

class ChatMessage(BaseModel):
    id: int
    content: str
    type: MessageType
    is_loading: bool = False
    search_info: Optional[SearchInfo] = None

class ChatRequest(BaseModel):
    message: str
    checkpoint_id: Optional[str] = None

class StreamResponse(BaseModel):
    type: str
    content: Optional[str] = None
    checkpoint_id: Optional[str] = None
    query: Optional[str] = None
    urls: Optional[List[str]] = None
    error: Optional[str] = None
