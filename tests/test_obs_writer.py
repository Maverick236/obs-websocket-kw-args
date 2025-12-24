import os
import tempfile
import time

import pytest

from almave7_system import obs_writer


def test_file_fallback_writes_file(tmp_path, monkeypatch):
    # Ensure websocket disabled so file path is used
    monkeypatch.setitem(obs_writer._WS_CONFIG, "enabled", False)

    p = tmp_path / "system.txt"
    text = "Hello OBS"

    obs_writer.write_obs(text, auto_clear=False, typed=False, path=str(p))

    assert p.exists()
    content = p.read_text(encoding="utf-8")
    # normalize possible stray null bytes from implementation details
    assert text in content.replace("\x00", "")


def test_ws_success_no_file_written(tmp_path, monkeypatch):
    # Simulate websocket path succeeding
    monkeypatch.setitem(obs_writer._WS_CONFIG, "enabled", True)

    # Prevent actual connection attempts
    monkeypatch.setattr(obs_writer, "_ensure_ws_connected", lambda: True)

    class DummyClient:
        def __init__(self):
            self.calls = []

        def call(self, req):
            self.calls.append(req)
            return None

    dummy = DummyClient()
    monkeypatch.setattr(obs_writer, "_WS_CLIENT", dummy)

    # Force obs call to succeed
    monkeypatch.setattr(obs_writer, "_obs_ws_set_text", lambda t: True)

    p = tmp_path / "system.txt"
    obs_writer.write_obs("From WS", auto_clear=False, typed=False, path=str(p))

    assert not p.exists()


def test_typing_creates_text_with_cursor_workflow(tmp_path, monkeypatch):
    # Ensure typing path: websocket disabled, typed True
    monkeypatch.setitem(obs_writer._WS_CONFIG, "enabled", False)

    # Speed up typing/cursor delays
    monkeypatch.setattr(obs_writer, "TYPE_DELAY", 0)
    monkeypatch.setattr(obs_writer, "CURSOR_BLINK_INTERVAL", 0)
    monkeypatch.setattr(obs_writer, "CURSOR_AFTER_SECONDS", 0)

    text = "TypeMe"
    p = tmp_path / "typed.txt"

    # Avoid running the complex typing implementation in unit tests; stub it.
    from pathlib import Path

    def _stub_type(text_arg, path_arg=None):
        path_obj = Path(path_arg) if path_arg is not None else Path(p)
        path_obj.write_text(text_arg + "\n", encoding="utf-8")

    monkeypatch.setattr(obs_writer, "_type_to_file", _stub_type)

    obs_writer.write_obs(text, auto_clear=False, typed=True, path=str(p))

    assert p.exists()
    content = p.read_text(encoding="utf-8")
    assert text in content
    assert content.endswith("\n")
# Additional tests: normalize legacy cases and ensure consistent behavior
def test_file_fallback(tmp_path, monkeypatch):
    out = tmp_path / "out.txt"
    # ensure websocket disabled
    monkeypatch.setitem(obs_writer._WS_CONFIG, "enabled", False)
    obs_writer.write_obs("hello world", auto_clear=False, path=str(out))
    assert out.exists()
    content = out.read_text(encoding="utf-8")
    assert "hello world" in content.replace("\x00", "")


def test_websocket_path(monkeypatch, tmp_path):
    out = tmp_path / "out_ws.txt"
    # ensure websocket enabled so code attempts websocket path
    monkeypatch.setitem(obs_writer._WS_CONFIG, "enabled", True)
    monkeypatch.setattr(obs_writer, "_obs_ws_set_text", lambda text: True)
    obs_writer.write_obs("from ws", auto_clear=False, path=str(out))
    # websocket path should not create a file
    assert not out.exists()


def test_typing_effect(tmp_path, monkeypatch):
    out = tmp_path / "out_type.txt"
    # speed up typing effect for test and stub complex typing
    monkeypatch.setattr(obs_writer, "TYPE_DELAY", 0)
    monkeypatch.setattr(obs_writer, "CURSOR_AFTER_SECONDS", 0)
    monkeypatch.setattr(obs_writer, "CURSOR_BLINK_INTERVAL", 0)

    from pathlib import Path

    def _stub_type(text_arg, path_arg=None):
        path_obj = Path(path_arg) if path_arg is not None else Path(out)
        path_obj.write_text(text_arg + "\n", encoding="utf-8")

    monkeypatch.setattr(obs_writer, "_type_to_file", _stub_type)
    obs_writer.write_obs("fast", auto_clear=False, typed=True, path=str(out))
    assert out.exists()
    content = out.read_text(encoding="utf-8")
    assert "fast" in content
