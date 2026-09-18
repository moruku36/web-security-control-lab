"""Pytest fixtures for Web Security Control Lab tests."""

import importlib
import os

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


@pytest.fixture
def lab_mode_app():
    """
    Factory fixture that builds a FastAPI app pinned to an explicit LAB_MODE,
    independent of the ambient LAB_MODE environment variable.

    app.config.LAB_MODE (and the values app.auth / app.main import from it)
    are bound once at module import time, so simply setting os.environ is not
    enough to change already-imported behavior. Reloading config -> db ->
    auth -> main in dependency order re-binds those constants for the
    requested mode. This lets regression tests assert the HARDENED security
    posture as a hard requirement, rather than only checking whatever mode
    the test process happened to start in.
    """
    import app.auth as auth_module
    import app.config as config_module
    import app.db as db_module
    import app.main as main_module

    original_env = os.environ.get("LAB_MODE")

    def _build(mode: str):
        os.environ["LAB_MODE"] = mode
        importlib.reload(config_module)
        importlib.reload(db_module)
        importlib.reload(auth_module)
        importlib.reload(main_module)
        db_module.get_db_connection()
        db_module.clear_audit_logs()
        return main_module.app

    try:
        yield _build
    finally:
        if original_env is None:
            os.environ.pop("LAB_MODE", None)
        else:
            os.environ["LAB_MODE"] = original_env
        importlib.reload(config_module)
        importlib.reload(db_module)
        importlib.reload(auth_module)
        importlib.reload(main_module)
