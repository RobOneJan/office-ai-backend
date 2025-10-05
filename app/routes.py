from pydantic import BaseModel
from typing import Optional
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from app.services import _init_vertexai, mask_with_dlp, restore_placeholders, call_vertexai
from app.db import SessionLocal
from app.models import Message, Conversation
from datetime import datetime
import json
import asyncio

router = APIRouter()

# --- Modelle für Swagger ---
class ChatRequest(BaseModel):
    conversation_id: Optional[int] = 1   # <--- int statt str
    user_id: int = 1
    tenant_id: int = 1
    message: str

class MaskRequest(BaseModel):
    text: str


# --- Normaler Chat ---
@router.post("/chat")
def chat(req: ChatRequest):
    result = call_vertexai(
        conversation_id=req.conversation_id,
        user_id=req.user_id,
        tenant_id=req.tenant_id,
        message=req.message
    )
    return result


# --- STREAMING Chat (Swagger sichtbar!) ---
@router.post("/chat/stream")
async def stream_chat(req: ChatRequest):
    model = _init_vertexai()
    masked_message, mapping = mask_with_dlp(req.message)

    db = SessionLocal()
    conversation = db.query(Conversation).filter_by(id=req.conversation_id).first()
    if not conversation:
        conversation = Conversation(id=req.conversation_id, user_id=req.user_id, tenant_id=req.tenant_id)
        db.add(conversation)
        db.commit()
        db.refresh(conversation)

    chat = model.start_chat()

    async def event_stream():
        full_response = ""
        for chunk in chat.send_message(masked_message, stream=True):
            if chunk.text:
                text = restore_placeholders(chunk.text, mapping)
                full_response += text
                yield f"data: {json.dumps({'text': text})}\n\n"
                await asyncio.sleep(0)  # damit FastAPI async streamt
        # Speichern nach kompletter Antwort
        db_message = Message(
            conversation_id=conversation.id,
            content=full_response,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.add(db_message)
        db.commit()

    return StreamingResponse(event_stream(), media_type="text/event-stream")


# --- Nur Masking ---
@router.post("/mask")
def mask_only(req: MaskRequest):
    masked, mapping = mask_with_dlp(req.text)
    return {"masked": masked, "mapping": mapping}
