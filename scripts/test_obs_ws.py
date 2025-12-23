"""Test OBS-WebSocket connectivity and set a text source if enabled.

Usage:
  python3 scripts/test_obs_ws.py

This script reads `config/system.yaml` and, if `obs_websocket.enabled` is true
and `obs-websocket-py` is installed, attempts to connect and set the configured
text source to a test string. It exits 0 on success or when skipped, and
non-zero on connection failures.
"""

from __future__ import annotations

from pathlib import Path
import sys

try:
    import yaml
except Exception:
    yaml = None

try:
    from obswebsocket import obsws, requests as obs_requests  # type: ignore
except Exception:
    obsws = None
    obs_requests = None

try:
    import websocket  # websocket-client
    import json, uuid, hashlib, base64
except Exception:
    websocket = None


def load_config():
    cfg = Path("config") / "system.yaml"
    if not cfg.exists() or yaml is None:
        return None
    try:
        data = yaml.safe_load(cfg.read_text(encoding="utf-8")) or {}
        return data.get("obs_websocket") or {}
    except Exception:
        return None


def main():
    ws = load_config()
    if not ws:
        print("OBS websocket not configured or PyYAML missing — skipping test.")
        return 0
    if not ws.get("enabled"):
        print("OBS websocket disabled in config — skipping test.")
        return 0
    if obsws is None:
        print("obs-websocket client not installed — skipping test.")
        return 0

    host = ws.get("host", "localhost")
    port = int(ws.get("port", 4444))
    password = ws.get("password", "")
    source = ws.get("source", "System Status")

    print(f"Attempting OBS WebSocket connection to {host}:{port} (source={source})...")
    try:
        client = obsws(host, port, password)
        client.connect()
    except Exception as e:
        msg = str(e)
        print("Connection failed:", msg)
        # If error looks like protocol mismatch, attempt v5 websocket fallback
        if websocket is None:
            return 2
        print("Attempting obs-websocket v5 fallback using raw websocket-client...")
        try:
            proto = "obswebsocket.json"
            ws_url = f"ws://{host}:{port}"
            ws = websocket.create_connection(ws_url, subprotocols=[proto], timeout=5)
            # receive Hello (op 0)
            raw = ws.recv()
            hello = json.loads(raw)
            if hello.get("op") != 0:
                print("Unexpected initial message from server:", hello)
                ws.close()
                return 2
            data = hello.get("d", {})
            auth = None
            if "authentication" in data and data.get("authentication"):
                # build authentication string per protocol
                challenge = data["authentication"].get("challenge")
                salt = data["authentication"].get("salt")
                # step1: base64_secret = base64_encode(sha256(password + salt))
                secret_bin = hashlib.sha256((password + salt).encode("utf-8")).digest()
                base64_secret = base64.b64encode(secret_bin).decode("utf-8")
                # step2: auth = base64_encode(sha256(base64_secret + challenge))
                auth_bin = hashlib.sha256((base64_secret + challenge).encode("utf-8")).digest()
                auth = base64.b64encode(auth_bin).decode("utf-8")

            # send Identify (op 1)
            identify = {"op": 1, "d": {"rpcVersion": 1}}
            if auth:
                identify["d"]["authentication"] = auth
            identify["d"]["eventSubscriptions"] = 0
            ws.send(json.dumps(identify))
            # receive Identified (op 2)
            raw2 = ws.recv()
            resp2 = json.loads(raw2)
            if resp2.get("op") != 2:
                print("Failed to identify with obs-websocket v5 server:", resp2)
                ws.close()
                return 2
            # prepare a SetInputSettings request (op 6)
            req_id = str(uuid.uuid4())
            req = {
                "op": 6,
                "d": {
                    "requestType": "SetInputSettings",
                    "requestId": req_id,
                    "requestData": {
                        "inputName": source,
                        "inputSettings": {"text": test_text},
                        "overlay": False,
                    },
                },
            }
            ws.send(json.dumps(req))
            # wait for response (op 7)
            raw3 = ws.recv()
            resp3 = json.loads(raw3)
            if resp3.get("op") == 7 and resp3.get("d", {}).get("requestId") == req_id:
                status = resp3.get("d", {}).get("requestStatus", {})
                if status.get("result"):
                    print("v5: SetInputSettings succeeded")
                    ws.close()
                    return 0
                else:
                    print("v5: request failed:", status)
                    ws.close()
                    return 3
            else:
                print("v5: unexpected response:", resp3)
                ws.close()
                return 2
        except Exception as e2:
            print("v5 fallback failed:", e2)
            return 2

    test_text = "[SYSTEM]: OBS-WebSocket test."
    try:
        # new obs-websocket-py versions expect keyword args
        try:
            client.call(obs_requests.SetTextGDIPlusProperties(source=source, text=test_text))
            print("SetTextGDIPlusProperties called.")
        except Exception:
            # fallback: use SetInputSettings with keyword args
            client.call(obs_requests.SetInputSettings(inputName=source, inputSettings={"text": test_text}, overlay=False))
            print("SetInputSettings called.")
    except Exception as e:
        print("Failed to set text on source:", e)
        client.disconnect()
        return 3

    client.disconnect()
    print("OBS-WebSocket test succeeded.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
