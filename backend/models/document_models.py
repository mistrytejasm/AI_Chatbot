from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class DocumentUploadResponse(BaseModel):
    document_id: str
    filename: str
    file_size: int
    content_type: str
    status: str
    upload_time: datetime
    total_chunks: Optional[int] = None

class DocumentChunk(BaseModel):
    chunk_id: str
    document_id: str
    content: str
    metadata: dict
    page_number: Optional[int] = None
    chunk_index: int
    
class DocumentQuery(BaseModel):
    query: str
    document_ids: Optional[List[str]] = None
    max_chunks: int = 5

class DocumentSearchResult(BaseModel):
    chunk_id: str
    content: str
    similarity_score: float
    metadata: dict
    page_number: Optional[int] = None