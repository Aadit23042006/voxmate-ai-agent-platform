from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.api.deps import get_current_user
from app.models.models import User, VoiceSession, ToolCall
from app.schemas import SearchHistoryOut

router = APIRouter(prefix="/history", tags=["history"])


@router.get("/search", response_model=List[SearchHistoryOut])
def list_search_history(
    limit: int = 50,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Returns this user's past 'search' tool calls, most recent first.
    Joins through VoiceSession since ToolCall only stores session_id.
    """
    rows = (
        db.query(ToolCall)
        .join(VoiceSession, ToolCall.session_id == VoiceSession.id)
        .filter(VoiceSession.user_id == user.id, ToolCall.tool_name == "search")
        .order_by(ToolCall.created_at.desc())
        .limit(limit)
        .all()
    )

    out = []
    for tc in rows:
        args = tc.arguments or {}
        result = tc.result or {}
        out.append(
            SearchHistoryOut(
                id=tc.id,
                query=args.get("query", ""),
                answer=result.get("answer"),
                sources=result.get("sources", []),
                status=tc.status,
                created_at=tc.created_at,
            )
        )
    return out


@router.delete("/search/{tool_call_id}")
def delete_search_history_item(
    tool_call_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Deletes a single search history entry, scoped to the current user
    so one user can't delete another user's history by guessing an id.
    """
    row = (
        db.query(ToolCall)
        .join(VoiceSession, ToolCall.session_id == VoiceSession.id)
        .filter(
            ToolCall.id == tool_call_id,
            VoiceSession.user_id == user.id,
            ToolCall.tool_name == "search",
        )
        .first()
    )
    if row is None:
        return {"deleted": False}
    db.delete(row)
    db.commit()
    return {"deleted": True}
