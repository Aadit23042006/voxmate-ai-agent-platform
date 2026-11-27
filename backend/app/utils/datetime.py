from datetime import datetime, timezone


def utcnow() -> datetime:
    """
    Return the current UTC time as a naive datetime.

    VoxMate currently uses SQLAlchemy DateTime columns without
    timezone=True, so database timestamps must remain naive UTC.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)
