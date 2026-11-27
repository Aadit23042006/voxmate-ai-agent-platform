import uuid
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.api.deps import get_current_user
from app.models.models import User, VoiceSession

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("")
def create_session(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Create a new voice session id. The mobile app calls this before
    opening the WebSocket connection to /ws/voice/{session_id}.
    """
    session_id = str(uuid.uuid4())
    vs = VoiceSession(id=session_id, user_id=user.id, status="pending")
    db.add(vs)
    db.commit()
    return {"session_id": session_id}
