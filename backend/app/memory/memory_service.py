"""Long-term memory service.

Existing Memory rows remain compatible. This layer adds:
- relevant (semantic/keyword) recall instead of only newest-N recall
- automatic extraction of explicit user facts/preferences
- optional embedding index in a separate table, so no existing column is changed
"""
import math
import re
from typing import List, Optional

from sqlalchemy.orm import Session
from app.models.models import Memory, MemoryEmbedding


def remember(db: Session, user_id: str, content: str, type_: str = "fact", confidence: float = 1.0):
    content = content.strip()
    if not content:
        return None

    # Avoid accumulating exact duplicates.
    existing = (
        db.query(Memory)
        .filter(Memory.user_id == user_id, Memory.content == content)
        .first()
    )
    if existing:
        return existing

    mem = Memory(user_id=user_id, type=type_, content=content, confidence=confidence)
    db.add(mem)
    db.commit()
    db.refresh(mem)

    # Semantic index is best-effort. If Gemini embeddings are unavailable,
    # keyword recall continues to work unchanged.
    try:
        from app.agents.llm_client import embed_text
        vector = embed_text(content)
        if vector:
            db.add(MemoryEmbedding(
                memory_id=mem.id, user_id=user_id, embedding=list(vector)
            ))
            db.commit()
    except Exception:
        db.rollback()
    return mem


def recall(db: Session, user_id: str, limit: int = 10):
    return (
        db.query(Memory)
        .filter(Memory.user_id == user_id)
        .order_by(Memory.created_at.desc())
        .limit(limit)
        .all()
    )


def recall_relevant(db: Session, user_id: str, query: str, limit: int = 8):
    """Prefer semantic matches when embeddings exist, otherwise keyword score."""
    memories = (
        db.query(Memory)
        .filter(Memory.user_id == user_id)
        .order_by(Memory.created_at.desc())
        .limit(200)
        .all()
    )
    if not memories:
        return []

    q_tokens = _tokens(query)
    semantic = {}
    try:
        from app.agents.llm_client import embed_text
        q_vector = embed_text(query)
        if q_vector:
            rows = db.query(MemoryEmbedding).filter(
                MemoryEmbedding.user_id == user_id
            ).all()
            for row in rows:
                semantic[str(row.memory_id)] = cosine_similarity(q_vector, row.embedding)
    except Exception:
        semantic = {}

    scored = []
    for mem in memories:
        tokens = _tokens(mem.content)
        overlap = len(q_tokens & tokens)
        recency_bonus = 0.05 if mem.created_at else 0
        score = overlap + recency_bonus + (semantic.get(str(mem.id), 0.0) * 3.0)
        scored.append((score, mem))
    scored.sort(key=lambda x: x[0], reverse=True)
    relevant = [m for score, m in scored if score > 0][:limit]
    return relevant or memories[:limit]


def remember_explicit_user_facts(db: Session, user_id: str, text: str) -> List[Memory]:
    """Capture only explicit statements, avoiding speculative memory."""
    text = (text or "").strip()
    candidates = []

    patterns = [
        (r"\bremember that\s+(.+)", "fact", 1.0),
        (r"\bmy name is\s+(.+)", "fact", 1.0),
        (r"\bi(?:'m| am)\s+from\s+(.+)", "fact", 0.95),
        (r"\bi (?:like|love|prefer)\s+(.+)", "preference", 0.9),
        (r"\bi (?:don't like|dislike|hate)\s+(.+)", "preference", 0.9),
        (r"\bmy favorite\s+(.+?)\s+is\s+(.+)", "preference", 0.95),
    ]
    for pattern, kind, confidence in patterns:
        match = re.search(pattern, text, flags=re.I)
        if match:
            phrase = " ".join(x.strip() for x in match.groups() if x.strip())
            if phrase:
                prefix = {
                    "fact": "User fact",
                    "preference": "User preference",
                }[kind]
                candidates.append((f"{prefix}: {phrase}", kind, confidence))

    stored = []
    for content, kind, confidence in candidates[:3]:
        mem = remember(db, user_id, content, kind, confidence)
        if mem:
            stored.append(mem)
    return stored


def build_memory_context(db: Session, user_id: str, query: str, limit: int = 8) -> str:
    memories = recall_relevant(db, user_id, query, limit)
    if not memories:
        return ""
    return "\n".join(f"- {m.content}" for m in memories)


def _tokens(text: str):
    return {
        t for t in re.findall(r"[a-zA-Z0-9']+", (text or "").lower())
        if len(t) > 2
    }


def cosine_similarity(a, b) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0
