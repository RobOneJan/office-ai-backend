from fastapi import APIRouter
from app.models.schemas import ChatRequest, ChatResponse
from app.services.vertex import ask_vertex

router = APIRouter()

@router.post("/", response_model=ChatResponse)
def chat_endpoint(request: ChatRequest):
    result = ask_vertex(request.user_message)
    return ChatResponse(
        conversation_id=request.conversation_id,
        bot_message=result["text"],
        token_usage=result["tokens"],
        cost_usd=result["cost_usd"]
    )

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
