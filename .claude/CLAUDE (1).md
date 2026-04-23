# CLAUDE.md — RFID Truck Scanner System

## Project Overview
This is an **industrial RFID truck gate management system**. Multiple RFID scanners are installed at entry/exit gates of a facility. When a truck passes through, the scanner reads the truck's RFID tag, and the system:
1. Identifies which scanner (gate) the truck passed through — **via IP address only**
2. Displays the truck's vehicle number and RFID tag in real time on a dashboard
3. Triggers a relay (gate open/close) and speaker (voice announcement) on the scanner

---

## Architecture — Always Follow This

```
RFID Scanner (TCP Socket)
        ↓
Python TCP Listener  ←─ rfid_server.py
        ↓
FastAPI + WebSocket  ←─ broadcasts every scan instantly
        ↓
Browser Dashboard    ←─ dashboard.html (real-time, no refresh)
```

**No database. No storage. No file writing.** Data flows live from scanner to screen only.
If storage is ever added in the future, it must not change this real-time flow — it should be additive only.

---

## Core Rule — IP is the Only Scanner Identity

- Each RFID scanner is identified **exclusively by its IP address**
- Never use scanner IDs, scanner names, or serial numbers as primary identifiers
- Every log entry and every event payload **must include the scanner IP**
- Location labels (Gate 1, Gate 2 etc.) are optional secondary metadata derived from the IP — never the primary key

---

## Tech Stack — Required

| Layer | Technology | Reason |
|---|---|---|
| Scanner communication | Python `asyncio` TCP socket | Scanners speak raw TCP, async keeps it non-blocking |
| Backend framework | **FastAPI** | Async-native, WebSocket built-in, lightweight |
| Real-time push | **WebSocket** (FastAPI `/ws`) | Pushes scan events to dashboard the instant they arrive |
| Frontend | Plain HTML + Vanilla JS | No build step, opens directly, works everywhere |
| Logging | Python `logging` | Never use `print()` in production |

---

## Project Structure

```
rfid-system/
├── rfid_server.py     # TCP listener + FastAPI + WebSocket broadcaster
├── dashboard.html     # Live browser dashboard — served by rfid_server.py
├── requirements.txt   # fastapi, uvicorn, websockets
└── CLAUDE.md
```

Keep it flat. Do not over-engineer the folder structure until storage or multi-scanner support is added.

---

## Configuration — Change Only These Two Lines

All scanner targeting lives at the top of `rfid_server.py`:

```python
SCANNER_IP   = "192.168.1.101"   # ← scanner IP here
SCANNER_PORT = 5000              # ← scanner port here
```

**Never hardcode an IP anywhere else.** When multi-scanner support is added later, these will move to a `config.py` — but not before.

---

## Dynamic Data Parser — Rules

The parser must handle all these formats with zero code changes:

| Format | Example |
|---|---|
| JSON | `{"rfid":"AB12CD34","vehicle":"MH12AB1234"}` |
| CSV | `AB12CD34,MH12AB1234` |
| Key=Value | `rfid=AB12CD34 vehicle=MH12AB1234` |
| Plain text | `MH12AB1234` |

Parser priority order:
1. Try JSON first
2. Fall back to key=value (if `=` present)
3. Fall back to CSV (if `,` present)
4. Final fallback: plain string, auto-label via regex

Rules:
- Auto-label values using regex — vehicle number pattern, hex RFID pattern, numeric ID
- **Never crash** on an unrecognised format — log a warning and continue
- Always pass the raw unparsed string through in the event payload alongside parsed fields

---

## TCP Listener — Rules

- Use `asyncio.open_connection` — not `threading`, not `socket` directly
- On disconnect: broadcast a `status` event to the dashboard, then auto-reconnect after 5 seconds
- On connection timeout or refusal: log the error, wait 5 seconds, retry — never crash
- Every received newline-delimited message → parse → broadcast immediately

---

## WebSocket Broadcast — Event Format

Every message sent to the dashboard must follow this shape:

```json
// Scan event
{
  "type": "scan",
  "scanner_ip": "192.168.1.101",
  "timestamp": "14:32:01",
  "raw": "<original string from scanner>",
  "fields": {
    "rfid_tag": "AB12CD34",
    "vehicle_number": "MH12AB1234"
  }
}

// Status event (on connect/disconnect)
{
  "type": "status",
  "scanner_ip": "192.168.1.101",
  "connected": true
}
```

---

## Dashboard — Requirements

- Connects to `/ws` on page load, auto-reconnects if dropped
- Shows a **live feed** of scan rows: timestamp, all parsed fields, raw toggle
- **Sidebar**: scanner IP, total scan count, last vehicle detected
- **Flash banner**: brief top-of-screen alert on every new scan
- Color codes: vehicle number in green, RFID tag in cyan, raw data in muted
- Status pill in header shows scanner online/offline state
- No page refresh ever needed

---

## Logging Rules

- Use Python `logging` — **never `print()`**
- Every log line must include: timestamp, event type, scanner IP, data
- Log levels: `INFO` for scans and connections, `WARNING` for parse failures, `ERROR` for connection drops

---

## Hard Rules — Never Break These

- ❌ No database, no file writes, no storage of any kind (until explicitly requested)
- ❌ Never identify a scanner by anything other than its IP
- ❌ Never hardcode an IP outside the two config lines at the top of `rfid_server.py`
- ❌ Never crash the listener on a bad data frame — log and continue
- ❌ Never mix relay/speaker logic into the parser or listener — keep separate
- ❌ Never use `print()` — use the logger
- ✅ Always auto-reconnect on socket drop
- ✅ Always include `scanner_ip` in every log line and every WebSocket event
- ✅ Always store the raw unparsed string alongside parsed fields in the event payload
- ✅ Always serve the dashboard from the Python server — never open `dashboard.html` as a file://
