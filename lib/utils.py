"""Small, self-contained helper functions."""

import random
import string
from datetime import datetime, timezone


def generate_case_number() -> str:
    """
    Make a short, human-friendly, anonymous case reference, e.g. 'CF-QWE1234'.
    This is what the employee saves to check on their case later — it carries
    no information that could identify them.
    """
    letters = "".join(random.choices(string.ascii_uppercase, k=3))
    digits = "".join(random.choices(string.digits, k=4))
    return f"CF-{letters}{digits}"


def now_iso() -> str:
    """Current UTC time as an ISO-8601 string, for storing on each case."""
    return datetime.now(timezone.utc).isoformat()
