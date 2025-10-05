from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from app.services import call_vertexai, mask_with_dlp, restore_placeholders

router = APIRouter()

from typing import Optional

class ChatRequest(BaseModel):
    conversation_id: Optional[int]  # <--- jetzt int und optional
    user_id: int                     
    tenant_id: int                   
    user_message: str
    debug: Optional[bool] = False

class MaskRequest(BaseModel):
    text: str

@router.post("/chat")
def chat(req: ChatRequest):
    result = call_vertexai(req.conversation_id, req.user_id, req.tenant_id, req.user_message)
    if not req.debug:
        result.pop("masked_message", None)
        result.pop("mapping", None)
    return result

@router.post("/mask")
def mask_only(req: MaskRequest):
    masked, mapping = mask_with_dlp(req.text)
    return {"masked": masked, "mapping": mapping}
