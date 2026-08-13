from fastapi import FastAPI

from app.routers.chat import router as chat_router
from app.routers.documents import router as documents_router


app = FastAPI(
    title="SCM RAG Assistant",
    description="SCM Knowledge Assistant using Microsoft Foundry",
    version="1.0.0",
)


app.include_router(chat_router)
app.include_router(documents_router)


@app.get("/health")
def health():
    return {
        "status": "UP"
    }