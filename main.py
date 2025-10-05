import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import router  # Dein Router mit /chat und /mask

app = FastAPI(title="OfficeAI Backend")

# --- CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Für Tests offen
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Router einbinden ---
app.include_router(router)

# --- Health Check ---
@app.get("/")
def health_check():
    return {"status": "ok"}

# --- Lokaler Start ---
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
