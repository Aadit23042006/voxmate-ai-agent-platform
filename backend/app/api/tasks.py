from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.api.deps import get_current_user
from app.models.models import User, Task
from app.schemas import TaskCreate, TaskOut

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("", response_model=List[TaskOut])
def list_tasks(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return db.query(Task).filter(Task.user_id == user.id).all()


@router.post("", response_model=TaskOut)
def create_task(payload: TaskCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    task = Task(user_id=user.id, title=payload.title, due_at=payload.due_at)
    db.add(task)
    db.commit()
    db.refresh(task)
    return task
