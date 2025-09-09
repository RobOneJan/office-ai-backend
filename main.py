from fastapi import FastAPI
from app.routes import router as api_router

app = FastAPI()

@app.get("/")
def health():
    return {"status": "ok"}

app.include_router(api_router, prefix="/api", tags=["api"])
