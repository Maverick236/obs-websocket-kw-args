import os
from pathlib import Path

import almave7_system.obs_writer as obs_writer


def test_file_fallback(tmp_path, monkeypatch):
    out = tmp_path / "out.txt"
    # ensure websocket disabled
    monkeypatch.setattr(obs_writer, "_WS_CONFIG", {"enabled": False, "host": "", "port": 0, "password": "", "source": ""})
    obs_writer.write_obs("hello world", auto_clear=False, path=str(out))
    assert out.exists()
    content = out.read_text(encoding="utf-8")
    assert "hello world" in content


def test_websocket_path(monkeypatch, tmp_path):
    out = tmp_path / "out_ws.txt"
    # force websocket success path
    monkeypatch.setattr(obs_writer, "_obs_ws_set_text", lambda text: True)
    obs_writer.write_obs("from ws", auto_clear=False, path=str(out))
    # websocket path should not create a file
    assert not out.exists()


def test_typing_effect(tmp_path, monkeypatch):
    out = tmp_path / "out_type.txt"
    # speed up typing effect for test
    monkeypatch.setattr(obs_writer, "TYPE_DELAY", 0)
    monkeypatch.setattr(obs_writer, "CURSOR_AFTER_SECONDS", 0)
    monkeypatch.setattr(obs_writer, "CURSOR_BLINK_INTERVAL", 0)
    obs_writer.write_obs("fast", auto_clear=False, typed=True, path=str(out))
    assert out.exists()
    content = out.read_text(encoding="utf-8")
    assert "fast" in content
