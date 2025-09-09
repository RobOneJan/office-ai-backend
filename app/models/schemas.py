from pydantic import BaseModel

class ChatRequest(BaseModel):
    conversation_id: str
    user_message: str

class ChatResponse(BaseModel):
    conversation_id: str
    bot_message: str
    token_usage: int
    cost_usd: float
