from uuid import uuid4
from fastapi import APIRouter, HTTPException
from app.capstone.schemas import ChatRequest, ChatResponse
from app.capstone.service import CapstoneService
from app.config import settings

router = APIRouter(prefix="/api", tags=["Task 6 Capstone"])
_sessions: dict[str, list[dict]] = {}
_service: CapstoneService | None = None

def _get_service() -> CapstoneService:
    global _service
    if _service is None:
        if not settings.gemini_api_key:
            raise HTTPException(status_code=503, detail="GEMINI_API_KEY is not configured.")
        _service = CapstoneService()
    return _service

@router.get("/capstone/health")
def capstone_health():
    return {"status": "ok", "gemini_configured": bool(settings.gemini_api_key), "feature": "task6-capstone"}

@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    service = _get_service()
    session_id = request.session_id or str(uuid4())
    history = _sessions.setdefault(session_id, [])
    try:
        result = service.run(request.message, history)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Gemini/agent execution failed: {exc}") from exc
    history.extend([{"role": "user", "content": request.message}, {"role": "assistant", "content": result["answer"]}])
    del history[:-12]
    return ChatResponse(session_id=session_id, **result)
