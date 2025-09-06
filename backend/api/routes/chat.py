from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
from typing import Optional
from services.chat_service import ChatService

router = APIRouter()
chat_service = ChatService()

@router.get("/chat_stream/{message}")
async def chat_stream(
    message: str,
    checkpoint_id: Optional[str] = Query(None)
):
    """Stream chat responses with search capabilities"""
    return StreamingResponse(
        chat_service.generate_response(message, checkpoint_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )

@router.get("/health-chat")
async def health_check():
    """Health check endpoint for chat service"""
    return {"status": "healthy", "service": "chat"}
