from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
import asyncio
import json
import uvicorn

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

scanner_connections = {}


class RFIDScanner:
    def __init__(self, websocket: WebSocket, scanner_id: str):
        self.websocket = websocket
        self.scanner_id = scanner_id
        self.running = False

    async def connect_to_scanner(self, ip_address: str, port: int = 5000):
        """Connect to RFID scanner via TCP"""
        self.running = True

        try:
            reader, writer = await asyncio.open_connection(ip_address, port)

            await self.websocket.send_json({
                "type": "connected",
                "scanner_id": self.scanner_id,
                "ip_address": ip_address
            })

            while self.running:
                data = await reader.read(1024)

                if not data:
                    break

                raw = data.decode(errors="ignore").strip()

                if not raw:
                    continue

                # Dynamic parser
                parsed = self.parse_data(raw)

                await self.websocket.send_json({
                    "type": "rfid_read",
                    "data": parsed,
                    "scanner_id": self.scanner_id,
                    "ip_address": ip_address
                })

        except Exception as e:
            await self.websocket.send_json({
                "type": "error",
                "message": f"Connection failed: {str(e)}"
            })

    def parse_data(self, raw):
        """Dynamic parser (JSON / CSV / key=value / plain)"""

        # JSON
        try:
            return json.loads(raw)
        except:
            pass

        # CSV
        if "," in raw:
            parts = raw.split(",")
            return {
                "rfid": parts[0],
                "vehicle": parts[1] if len(parts) > 1 else None
            }

        # key=value
        if "=" in raw:
            data = {}
            for part in raw.split():
                if "=" in part:
                    k, v = part.split("=")
                    data[k] = v
            return data

        # fallback
        return {"raw_data": raw}


@app.websocket("/ws/scanner/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await websocket.accept()

    scanner = RFIDScanner(websocket, client_id)
    scanner_connections[client_id] = scanner

    try:
        while True:
            message = await websocket.receive_text()
            data = json.loads(message)

            if data.get("action") == "connect":
                ip_address = data.get("ip_address")
                port = data.get("port", 5000)

                # ✅ Run in background (IMPORTANT FIX)
                asyncio.create_task(
                    scanner.connect_to_scanner(ip_address, port)
                )

            elif data.get("action") == "disconnect":
                scanner.running = False
                await websocket.send_json({"type": "disconnected"})

    except WebSocketDisconnect:
        scanner.running = False
        scanner_connections.pop(client_id, None)


@app.get("/")
async def get_root():
    return HTMLResponse(HTML_CONTENT)


with open("index.html", "r") as f:
    HTML_CONTENT = f.read()


@app.get("/api/my-ip")
async def get_my_ip():
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return {"ip": ip}
    except:
        return {"ip": "127.0.0.1"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)