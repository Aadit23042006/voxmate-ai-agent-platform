from pathlib import Path
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import Base, engine
from app.models import models  # noqa: F401  (ensures models are registered)
from app.api import auth, tasks, sessions, history, account, integrations, documents, meetings, research, platform, capstone
from app.realtime import voice_gateway

logging.basicConfig(level=settings.log_level)

@asynccontextmanager
async def lifespan(_app: FastAPI):
    # For a real project, use Alembic migrations instead of create_all.
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="VoxMate API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.cors_allowed_origins.split(",") if origin.strip()],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


app.include_router(auth.router)
app.include_router(tasks.router)
app.include_router(sessions.router)
app.include_router(history.router)
app.include_router(account.router)
app.include_router(integrations.router)
app.include_router(documents.router)
app.include_router(meetings.router)
app.include_router(research.router)
app.include_router(platform.router)
app.include_router(capstone.router)
app.include_router(voice_gateway.router)

# Task 6 deployable web interface. API routes remain available under /api and /ws.
app.mount("/", StaticFiles(directory=str(Path(__file__).resolve().parent / "static"), html=True), name="task6-web")


