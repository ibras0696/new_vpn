from types import SimpleNamespace

import pytest

from services import xray_client as xc


class DummyResult:
    def __init__(self, returncode: int = 0, stdout: str = "", stderr: str = "") -> None:
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def test_check_xray_api_success(monkeypatch):
    monkeypatch.setattr(xc, "_run_xray_api", lambda *a, **k: DummyResult())
    assert xc.check_xray_api() is True


def test_check_xray_api_failure(monkeypatch):
    def _raise(*args, **kwargs):
        raise xc.XRayAPIError(["xray"], 1, "", "boom")

    monkeypatch.setattr(xc, "_run_xray_api", _raise)
    assert xc.check_xray_api() is False


def test_remove_vless_user_ignore_missing(monkeypatch):
    error = xc.XRayAPIError(["xray"], 1, "", "user not found")
    monkeypatch.setattr(xc, "_run_xray_api", lambda *a, **k: (_ for _ in ()).throw(error))

    assert xc.remove_vless_user("test@example.com", ignore_missing=True) is False


def test_add_vless_user_duplicate(monkeypatch):
    key = SimpleNamespace(id="123e4567-e89b-12d3-a456-426614174000")
    error = xc.XRayAPIError(["xray"], 1, "", "already existed")

    def _raise(*args, **kwargs):
        raise error

    monkeypatch.setattr(xc, "_run_xray_api", _raise)
    assert xc.add_vless_user(key) is False


def test_add_vless_user_success(monkeypatch):
    key = SimpleNamespace(id="123e4567-e89b-12d3-a456-426614174111")
    monkeypatch.setattr(xc, "_run_xray_api", lambda *a, **k: DummyResult())
    assert xc.add_vless_user(key) is True
