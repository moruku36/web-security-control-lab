"""Unit tests for scanner target safety validation."""

import pytest

from scanner.target import is_safe_target, validate_target_url


def test_safe_local_targets_allowed():
    assert is_safe_target("http://localhost:8000") is True
    assert is_safe_target("http://127.0.0.1:8000") is True
    assert is_safe_target("http://127.0.0.1") is True
    assert is_safe_target("http://[::1]:8000") is True
    assert is_safe_target("http://web-security-control-lab-app:8000") is True


def test_validate_target_url_normalizes_and_returns():
    url = validate_target_url("http://127.0.0.1:8000/")
    assert url == "http://127.0.0.1:8000"


def test_prohibited_remote_targets_rejected():
    prohibited_targets = [
        "https://example.com",
        "https://google.com",
        "http://192.168.1.1:8000",
        "http://10.0.0.1:8000",
        "http://172.16.0.1:8000",
        "http://8.8.8.8",
        "http://attacker.example.org",
        "ftp://127.0.0.1",
        "javascript:alert(1)",
        "",
        None,
    ]

    for target in prohibited_targets:
        assert is_safe_target(target) is False
        with pytest.raises(ValueError, match="Refusing target"):
            validate_target_url(target)
