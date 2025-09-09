import os
from fastapi import FastAPI
from pydantic import BaseModel
from app.services import call_vertexai

app = FastAPI()


class ChatRequest(BaseModel):
    conversation_id: str
    user_message: str


@app.get("/")
def health_check():
    return {"status": "ok"}


@app.post("/chat")
def chat(req: ChatRequest):
    result = call_vertexai(req.conversation_id, req.user_message)
    return {
        "conversation_id": req.conversation_id,
        **result
    }


# Lokaler Start (optional)
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8081))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
