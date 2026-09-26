from fastapi import FastAPI, HTTPException
from app.api.v1 import reports
from app.core.config import settings

app = FastAPI(title=settings.PROJECT_NAME, version=settings.VERSION)

app.include_router(reports.router, prefix="/api/v1")

@app.get("/health")
async def health_check():
    return {"status": "ok"}
