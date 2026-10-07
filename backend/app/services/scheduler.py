"""Real UTC scheduling. No inferred platform outcomes or synthetic clock."""
from datetime import datetime, timezone

def now(db=None):
    return datetime.now(timezone.utc)

def check_due(db):
    # Observation providers must return evidence before a case can change state.
    # No response is inferred merely because a scheduled deadline passed.
    raise RuntimeError("Follow-up observation provider unavailable; no case state changed")
