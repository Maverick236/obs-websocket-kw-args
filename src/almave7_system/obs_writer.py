from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Optional

try:
    import yaml
except Exception:
    yaml = None

try:
    from obswebsocket import obsws, requests as obs_requests  # type: ignore
except Exception:
    obsws = None
    obs_requests = None


# OBS writer: centralizes file-based and typing behaviors for OBS text sources.
IDLE_TEXT = "[SYSTEM]: System idle."
CLEAR_SECONDS = 5

# Typing effect configuration
TYPE_TO_OBS = True
TYPE_DELAY = 0.04  # seconds per character
CURSOR_CHAR = "_"
CURSOR_BLINK_INTERVAL = 0.45
CURSOR_AFTER_SECONDS = 1.8

# Messages that should never be typed; always write instantly.
NON_TYPED_TEXTS = {IDLE_TEXT, "[SYSTEM]: System ready."}


# WebSocket config (populated from config/system.yaml when available)
_WS_CONFIG = {
    "enabled": False,
    "host": "localhost",
    "port": 4444,
    "password": "",
    "source": "System Status",
}

_WS_CLIENT = None


def _load_ws_config() -> None:
    """Load obs_websocket config from `config/system.yaml` if present and PyYAML available."""
    global _WS_CONFIG
    cfg_path = Path("config") / "system.yaml"
    if not cfg_path.exists() or yaml is None:
        return
    try:
        data = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
        ws = data.get("obs_websocket") or {}
        if isinstance(ws, dict):
            for k in _WS_CONFIG.keys():
                if k in ws:
                    _WS_CONFIG[k] = ws[k]
    except Exception:
        return


def _ensure_ws_connected() -> bool:
    """Ensure a websocket client is connected if configured. Returns True on success."""
    global _WS_CLIENT
    if not _WS_CONFIG.get("enabled"):
        return False
    if obsws is None:
        return False
    if _WS_CLIENT is not None:
        return True
        try:
            # prefer explicit config password, fall back to environment variable OBS_PASSWORD
            password = _WS_CONFIG.get("password") or os.environ.get("OBS_PASSWORD", "")
            _WS_CLIENT = obsws(_WS_CONFIG["host"], int(_WS_CONFIG["port"]), password)
        _WS_CLIENT.connect()
        return True
    except Exception:
        _WS_CLIENT = None
        return False


def _write_obs_now(text: str, path: Optional[Path] = None) -> None:
    path = path or (Path("obs") / "system.txt")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")


def _type_to_file(text: str, path: Optional[Path] = None) -> None:
    path = path or (Path("obs") / "system.txt")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        f.write("")
        f.flush()
        for ch in text:
            f.write(ch)
            f.flush()
            # show cursor, then remove it so cursor blinks while typing
            f.write(CURSOR_CHAR)
            f.flush()
            time.sleep(TYPE_DELAY)
            # remove cursor
            f.seek(0, 2)
            pos = f.tell()
            if pos > 0:
                f.truncate(pos - len(CURSOR_CHAR))
                f.flush()

        # after typing, blink the cursor for a short duration
        end_time = time.time() + CURSOR_AFTER_SECONDS
        while time.time() < end_time:
            f.write(CURSOR_CHAR)
            f.flush()
            time.sleep(CURSOR_BLINK_INTERVAL)
            f.seek(0, 2)
            pos = f.tell()
            if pos > 0:
                f.truncate(pos - len(CURSOR_CHAR))
                f.flush()

        f.write("\n")
        f.flush()


def _obs_ws_set_text(text: str) -> bool:
    """Attempt to set text on configured OBS text source via WebSocket.

    Returns True on success, False otherwise.
    """
    if not _ensure_ws_connected():
        return False
    try:
        # prefer SetTextGDIPlusProperties (classic text source)
        try:
            # prefer SetTextGDIPlusProperties (classic text source) with keyword args
            _WS_CLIENT.call(obs_requests.SetTextGDIPlusProperties(source=_WS_CONFIG["source"], text=text))
            return True
        except Exception:
            pass

        # fallback: SetInputSettings for modern sources (keyword args)
        try:
            settings = {"text": text}
            _WS_CLIENT.call(obs_requests.SetInputSettings(inputName=_WS_CONFIG["source"], inputSettings=settings, overlay=False))
            return True
        except Exception:
            return False
    except Exception:
        return False


def write_obs(text: str, auto_clear: bool = True, typed: Optional[bool] = None, path: Optional[str] = None) -> None:
    """Write a message for OBS. If typing is enabled, simulate typing.

    `typed` overrides global `TYPE_TO_OBS` when not None. None => use global.
    If OBS WebSocket is enabled and available, try that first and fall back to file writes.
    """
    # Load websocket config (no-op if yaml not available)
    _load_ws_config()

    enabled = TYPE_TO_OBS if typed is None else bool(typed)
    if text.strip() in NON_TYPED_TEXTS:
        enabled = False

    # If websocket enabled and client available, prefer it (no typing on websocket)
    if _WS_CONFIG.get("enabled") and _obs_ws_set_text(text):
        if auto_clear:
            # schedule file-based idle write as well to keep file in sync
            t = threading.Timer(CLEAR_SECONDS, lambda: _write_obs_now(IDLE_TEXT))
            t.daemon = True
            t.start()
        return

    p = Path(path) if path else (Path("obs") / "system.txt")

    if enabled:
        _type_to_file(text, p)
    else:
        _write_obs_now(text, p)

    if auto_clear:
        t = threading.Timer(CLEAR_SECONDS, lambda: _write_obs_now(IDLE_TEXT, p))
        t.daemon = True
        t.start()

