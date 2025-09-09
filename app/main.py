import os
from fastapi import FastAPI
from google.oauth2 import service_account
import vertexai
from vertexai.generative_models import GenerativeModel
from app.chat import router as chat_router
import uvicorn

# --- Init Credentials ---
key_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
if not key_path:
    raise ValueError("GOOGLE_APPLICATION_CREDENTIALS env var not set")

credentials = service_account.Credentials.from_service_account_file(key_path)

vertexai.init(
    project="dev-truth-471209-h0",
    location="global",
    credentials=credentials
)

# --- FastAPI App ---
app = FastAPI()
app.include_router(chat_router, prefix="/chat", tags=["chat"])

@app.get("/")
def health_check():
    return {"status": "ok"}

@app.post("/chat")
def chat(conversation_id: str, user_message: str):
    model = GenerativeModel("gemini-2.5-flash")
    response = model.generate_content(user_message)
    return {
        "conversation_id": conversation_id,
        "bot_message": response.text,
        "token_usage": None,
        "cost_usd": None,
    }

if __name__ == "__main__":
    
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
