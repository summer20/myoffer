import sys

from app.config import _default_database_url


def test_default_database_url_uses_relative_path_when_not_frozen(monkeypatch):
    monkeypatch.setattr(sys, "frozen", False, raising=False)
    assert _default_database_url() == "sqlite:///./myoffer.db"


def test_default_database_url_uses_exe_directory_when_frozen(monkeypatch, tmp_path):
    exe_path = tmp_path / "MyOffer.exe"
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(exe_path), raising=False)
    expected = f"sqlite:///{tmp_path.as_posix()}/myoffer.db"
    assert _default_database_url() == expected
