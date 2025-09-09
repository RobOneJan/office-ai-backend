from fastapi import APIRouter
from pydantic import BaseModel
from app.services import call_vertex

router = APIRouter()

class ChatRequest(BaseModel):
    message: str

@router.post("/chat")
def chat(req: ChatRequest):
    reply = call_vertex(req.message)
    return {"reply": reply}
