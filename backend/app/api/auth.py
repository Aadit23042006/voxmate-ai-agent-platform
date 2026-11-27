from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.models import User
from app.schemas import RegisterRequest, LoginRequest, TokenResponse
from app.security import hash_password, verify_password, create_access_token

router = APIRouter(prefix="/auth", tags=["auth"])


def _normalize_email(email: str) -> str:
    """Normalize email consistently for registration and login."""
    return email.strip().casefold()


@router.post("/register", response_model=TokenResponse)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    email = _normalize_email(payload.email)
    existing = (
        db.query(User)
        .filter(func.lower(func.trim(User.email)) == email)
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(email=email, hashed_password=hash_password(payload.password))
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(subject=user.id)
    return TokenResponse(access_token=token)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    email = _normalize_email(payload.email)
    user = (
        db.query(User)
        .filter(func.lower(func.trim(User.email)) == email)
        .first()
    )

    # Treat malformed/legacy password hashes as invalid credentials without
    # exposing implementation details or turning the endpoint into a 500.
    password_matches = False
    if user:
        try:
            password_matches = verify_password(payload.password, user.hashed_password)
        except Exception:
            password_matches = False

    if not user or not password_matches:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    token = create_access_token(subject=user.id)
    return TokenResponse(access_token=token)
