"""Check OBS scenes and sources using obs-websocket.

Usage:
  python scripts/check_obs_sources.py

The script will:
 - load `config/system.yaml` if present
 - prefer `OBS_PASSWORD` env var when password is blank
 - attempt to connect to OBS WebSocket and list scenes/inputs
 - check whether the `source` configured exists

This script is safe to run locally; if the obs-websocket client or PyYAML
isn't installed it will print instructions instead of failing.
"""

from pathlib import Path
import os
import sys

try:
    import yaml
except Exception:
    yaml = None

try:
    from obswebsocket import obsws, requests as obs_requests
except Exception:
    obsws = None
    obs_requests = None


def load_config():
    cfg = {
        "enabled": False,
        "host": "localhost",
        "port": 4455,
        "password": "",
        "source": "System Status",
    }
    p = Path("config") / "system.yaml"
    if p.exists() and yaml is not None:
        try:
            data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
            ws = data.get("obs_websocket") or {}
            if isinstance(ws, dict):
                for k in cfg.keys():
                    if k in ws:
                        cfg[k] = ws[k]
        except Exception as e:
            print("Failed to parse config/system.yaml:", e)
    return cfg


def main():
    cfg = load_config()
    print("OBS config:")
    for k in ("enabled", "host", "port", "source"):
        print(f"  {k}: {cfg.get(k)!r}")

    password = cfg.get("password") or os.environ.get("OBS_PASSWORD") or ""
    if not cfg.get("enabled"):
        print("WebSocket is disabled in config. Enable it to run checks.")
        return 0

    if obsws is None:
        print("obs-websocket client not installed. Install with:")
        print("  pip install obs-websocket-py websocket-client PyYAML")
        return 2

    try:
        ws = obsws(cfg["host"], int(cfg["port"]), password)
        ws.connect()
    except Exception as e:
        print("Failed to connect to OBS WebSocket:", e)
        return 3

    try:
        # get scene list
        scenes = ws.call(obs_requests.GetSceneList())
        scene_names = [s["name"] for s in scenes.getScenes()]
        print("Scenes:")
        for s in scene_names:
            print(" -", s)

        # get inputs (sources)
        inputs = ws.call(obs_requests.GetInputList())
        input_names = [i["inputName"] for i in inputs.getInputs()]
        print("Inputs/Sources:")
        for i in input_names:
            print(" -", i)

        # check configured source
        configured = cfg.get("source")
        if configured in input_names:
            print(f"Configured source '{configured}' FOUND in inputs.")
        else:
            print(f"Configured source '{configured}' NOT found. Check scene collection and source names.")

    except Exception as e:
        print("Error while querying OBS:", e)
        return 4
    finally:
        try:
            ws.disconnect()
        except Exception:
            pass

    return 0


if __name__ == "__main__":
    sys.exit(main())
