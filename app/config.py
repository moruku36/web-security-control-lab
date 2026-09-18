"""Lab application configuration."""

import os
from enum import Enum


class LabMode(str, Enum):
    VULNERABLE = "VULNERABLE"
    HARDENED = "HARDENED"


# Default mode is VULNERABLE for initial educational state
LAB_MODE: str = os.getenv("LAB_MODE", LabMode.VULNERABLE.value)

# TEST CREDENTIALS - DO NOT USE IN PRODUCTION
# Explicit mock fixtures strictly for local educational lab demonstration
DEFAULT_FIXTURE_USERS = [
    {
        "username": "alice",
        "password": "user",
        "role": "user",
        "display_name": "Alice User",
    },
    {
        "username": "admin",
        "password": "admin",
        "role": "admin",
        "display_name": "Lab Administrator",
    },
]

SESSION_COOKIE_NAME = "lab_session"
DB_PATH = os.getenv("LAB_DB_PATH", ":memory:")
