"""Pytest fixtures for Web Security Control Lab tests."""

import pytest
from starlette.testclient import TestClient

from app.config import LAB_MODE
from app.db import clear_audit_logs, get_db_connection, init_db
from app.main import app


@pytest.fixture(autouse=True)
def reset_database():
    """Reset database and seed fixtures before each test."""
    conn = get_db_connection()
    init_db(conn)
    clear_audit_logs()
    yield


@pytest.fixture
def client():
    """Synchronous test client."""
    with TestClient(app, base_url="http://127.0.0.1:8000", cookies={}) as c:
        yield c


@pytest.fixture
def current_lab_mode():
    return LAB_MODE
