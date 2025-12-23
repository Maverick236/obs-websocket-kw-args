# OBS WebSocket Setup and Troubleshooting

This document describes how to configure OBS WebSocket (obs-websocket) for use with the `almave7_system` project, firewall rules, and quick verification steps from the Linux control machine.

## Goals
- Enable obs-websocket server in OBS
- Ensure the server port/password match `config/system.yaml`
- Provide steps to allow remote connections and verify connectivity

## OBS (Windows) — Server Settings
1. Open OBS.
2. Tools → WebSockets Server Settings (or obs-websocket Server Settings).
3. Configure:
   - Enable WebSocket server: checked
   - Server Port: `4455` (or any free port you prefer)
   - Enable Authentication: checked
   - Server Password: `Almave7` (or a secure password — must match `config/system.yaml`)
4. For legacy/v4 compatibility (compat server): either disable it, or set a different port so it does not conflict with the main server.
5. Click Apply, then restart OBS.

## Windows — Verify OBS Listening
Open an elevated PowerShell and run:

```powershell
netstat -ano | findstr :4455
# or (PowerShell native):
Get-NetTCPConnection -LocalPort 4455
# find the process owning the PID:
tasklist /FI "PID eq <PID>"
```

If OBS is listening you should see a `LISTENING` entry; the PID should map to `obs64.exe`.

## Windows — Open Firewall Port (if remote connections required)
Run (PowerShell as Admin):

```powershell
New-NetFirewallRule -DisplayName "OBS WebSocket 4455" -Direction Inbound -Action Allow -Protocol TCP -LocalPort 4455
```

## Project config (`config/system.yaml`)
Make sure the YAML contains the obs_websocket block that matches OBS settings:

```yaml
obs_websocket:
  enabled: true
  host: 172.25.224.1   # set to OBS machine IP or localhost if OBS runs locally
  port: 4455
  password: "Almave7"
  source: System Status
```

Place the file at `Projects/almave7_system/config/system.yaml`.

## Linux — Verify Reachability
From the control machine run:

```bash
nc -vz <OBS_IP> 4455
# or with Python's socket (quick):
python3 -c "import socket; s=socket.socket(); s.settimeout(3); s.connect((\"<OBS_IP>\",4455)); print('ok')"
```

If the connection succeeds, run the project's test script from the project root:

```bash
/home/almave7/claude_env/bin/python /home/almave7/Projects/almave7_system/scripts/test_obs_ws.py
```

Expected output:
- `Attempting OBS WebSocket connection to <IP>:4455...`
- `SetTextGDIPlusProperties called.`
- `OBS-WebSocket test succeeded.`

## Troubleshooting
- `Connection refused` — server not listening on that host:port; verify OBS settings and that OBS is running.
- `Connection timed out` — likely firewall or network routing issue; add firewall rule, check NAT/VPN.
- `Baserequests.__init__() takes 1 positional argument but 4 were given` — indicates an incompatible `obs-websocket-py` API call; the project includes fallbacks and has been patched to use keyword args. If you see similar errors, ensure `obs-websocket-py` and `websocket-client` are installed in the Python environment used to run scripts.

## Notes
- The project includes `src/almave7_system/obs_writer.py` which prefers WebSocket updates and falls back to file writes (`obs/system.txt`) when WebSocket is unavailable.
- The `scripts/test_obs_ws.py` script is a small, standalone test that sets a configured text source and exercises both classic (GDI+) and modern input settings paths.

If you want, I can add a short `OBS_SETUP.md` entry to the top-level docs or create a small troubleshooting checklist in `README.md`.
