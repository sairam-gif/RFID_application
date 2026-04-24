from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
import json
import socket
import asyncio
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
        """
        Connect to RFID scanner (FX9600) via TCP.
        - Auto‑reconnects if the scanner closes the connection.
        - Sends JSON events to WebSocket.
        """
        self.running = True
        while self.running:
            try:
                reader, writer = await asyncio.open_connection(ip_address, port)

                await self.websocket.send_json(
                    {
                        "type": "connected",
                        "scanner_id": self.scanner_id,
                        "ip_address": ip_address,
                        "port": port,
                    }
                )

                while self.running:
                    try:
                        data = await reader.read(1024)
                        if not data:
                            # FX9600 closed the TCP connection
                            await self.websocket.send_json(
                                {
                                    "type": "disconnected",
                                    "message": "Scanner closed connection",
                                    "scanner_id": self.scanner_id,
                                }
                            )
                            break

                        raw = data.decode(errors="ignore").strip()
                        if not raw:
                            continue

                        parsed = self.parse_data(raw)
                        await self.websocket.send_json(
                            {
                                "type": "rfid_read",
                                "data": parsed,
                                "scanner_id": self.scanner_id,
                                "ip_address": ip_address,
                            }
                        )
                    except Exception as e:
                        await self.websocket.send_json(
                            {
                                "type": "error",
                                "message": f"Read error: {str(e)}",
                                "scanner_id": self.scanner_id,
                            }
                        )
                        break  # exit inner loop, then reconnect

                # Close TCP socket and reconnect after delay
                writer.close()
                await writer.wait_closed()
                await asyncio.sleep(3)

            except Exception as e:
                await self.websocket.send_json(
                    {
                        "type": "error",
                        "message": f"Connect error: {str(e)}",
                        "scanner_id": self.scanner_id,
                    }
                )
                if not self.running:
                    break
                await asyncio.sleep(3)

    def parse_data(self, raw):
        """
        Try to parse raw line from FX9600 in several formats:
        - JSON
        - CSV (e.g., tag,vehicle)
        - key=value (e.g., rfid=12345)
        - fallback: just raw text.
        """
        # JSON
        try:
            return json.loads(raw)
        except Exception:
            pass

        # CSV: assume tag,vehicle,... as first two fields
        if "," in raw:
            parts = raw.split(",")
            return {
                "rfid": parts[0].strip(),
                "vehicle": parts[1].strip() if len(parts) > 1 else None,
            }

        # key=value style
        if "=" in raw:
            data = {}
            for part in raw.split():
                if "=" in part:
                    try:
                        k, v = part.split("=", 1)
                        data[k.strip()] = v.strip()
                    except Exception:
                        pass
            return data

        # fallback
        return {"raw_data": raw}


@app.websocket("/ws/scanner/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """
    WebSocket endpoint for one scanner client.
    - Receives "connect" and "disconnect" commands from client.
    - Starts TCP connection to FX9600.
    """
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

                if scanner.running:
                    await websocket.send_json(
                        {
                            "type": "error",
                            "message": "Already connected",
                            "scanner_id": client_id,
                        }
                    )
                else:
                    asyncio.create_task(
                        scanner.connect_to_scanner(ip_address, port)
                    )

            elif data.get("action") == "disconnect":
                scanner.running = False
                await websocket.send_json(
                    {
                        "type": "disconnected",
                        "scanner_id": client_id,
                    }
                )

    except WebSocketDisconnect:
        scanner.running = False
        scanner_connections.pop(client_id, None)


@app.get("/")
async def get_root():
    """
    Simple HTML page that shows how to use the WebSocket (for demo).
    """
    return HTMLResponse(HTML_CONTENT)


# Load HTML content from file
with open("index.html", "r") as f:
    HTML_CONTENT = f.read()


@app.get("/api/my-ip")
async def get_my_ip():
    """
    Return this machine’s local IP (for client troubleshooting).
    """
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return {"ip": ip}
    except Exception:
        return {"ip": "127.0.0.1"}


if __name__ == "__main__":
    # Run FastAPI server on all interfaces, port 5000
    uvicorn.run(app, host="0.0.0.0", port=5000)