from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
import json
import socket
import asyncio
import uvicorn
import httpx


app = FastAPI()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


device_connections = {}


class DeviceCommunicator:
    def __init__(self, websocket: WebSocket, client_id: str):
        self.websocket = websocket
        self.client_id = client_id
        self.running = False

    async def connect_tcp(self, ip_address: str, port: int = 5000):
        """
        Connect to a device via TCP.
        - Auto-reconnects if the connection is lost.
        """
        self.running = True
        while self.running:
            try:
                reader, writer = await asyncio.open_connection(ip_address, port)

                await self.websocket.send_json(
                    {
                        "type": "connected",
                        "protocol": "tcp",
                        "client_id": self.client_id,
                        "ip_address": ip_address,
                        "port": port,
                    }
                )

                while self.running:
                    try:
                        data = await reader.read(4096)  # Increased buffer size
                        if not data:
                            await self.websocket.send_json(
                                {
                                    "type": "disconnected",
                                    "message": "Device closed TCP connection",
                                    "client_id": self.client_id,
                                }
                            )
                            break

                        raw = data.decode(errors="ignore").strip()
                        if not raw:
                            continue

                        # Handle multiple lines if they come in one chunk
                        lines = raw.splitlines()
                        for line in lines:
                            if not line.strip(): continue
                            parsed = self.parse_data(line.strip())
                            await self.websocket.send_json(
                                {
                                    "type": "data_received",
                                    "data": parsed,
                                    "client_id": self.client_id,
                                    "ip_address": ip_address,
                                    "protocol": "tcp"
                                }
                            )
                    except Exception as e:
                        await self.websocket.send_json(
                            {
                                "type": "error",
                                "message": f"TCP Read error: {str(e)}",
                                "client_id": self.client_id,
                            }
                        )
                        break

                writer.close()
                await writer.wait_closed()
                if self.running:
                    await asyncio.sleep(3)

            except Exception as e:
                await self.websocket.send_json(
                    {
                        "type": "error",
                        "message": f"TCP Connect error: {str(e)}",
                        "client_id": self.client_id,
                    }
                )
                if not self.running:
                    break
                await asyncio.sleep(3)

    async def fetch_http(self, ip_address: str, port: int = 80, path: str = "/", interval: int = 5):
        """
        Fetch data from a device via HTTP GET polling.
        """
        self.running = True
        url = f"http://{ip_address}:{port}{path}"
        
        async with httpx.AsyncClient() as client:
            await self.websocket.send_json(
                {
                    "type": "connected",
                    "protocol": "http",
                    "client_id": self.client_id,
                    "url": url,
                    "interval": interval
                }
            )
            
            while self.running:
                try:
                    response = await client.get(url, timeout=10.0)
                    raw = response.text.strip()
                    
                    if raw:
                        parsed = self.parse_data(raw)
                        await self.websocket.send_json(
                            {
                                "type": "data_received",
                                "data": parsed,
                                "client_id": self.client_id,
                                "ip_address": ip_address,
                                "protocol": "http",
                                "status_code": response.status_code
                            }
                        )
                except Exception as e:
                    await self.websocket.send_json(
                        {
                            "type": "error",
                            "message": f"HTTP Fetch error: {str(e)}",
                            "client_id": self.client_id,
                        }
                    )
                
                await asyncio.sleep(interval)

    def parse_data(self, raw):
        """
        Generic parser for various data formats.
        """
        # 1. Try JSON
        try:
            return json.loads(raw)
        except Exception:
            pass

        # 2. Try CSV/Comma-separated
        if "," in raw:
            parts = [p.strip() for p in raw.split(",")]
            if len(parts) > 1:
                return {f"field_{i+1}": p for i, p in enumerate(parts)}

        # 3. Try key=value style
        if "=" in raw:
            data = {}
            # Split by whitespace or semicolons
            parts = raw.replace(";", " ").split()
            for part in parts:
                if "=" in part:
                    try:
                        k, v = part.split("=", 1)
                        data[k.strip()] = v.strip()
                    except Exception:
                        pass
            if data:
                return data

        # 4. Fallback to raw text
        return {"raw_data": raw}


@app.websocket("/ws/device/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await websocket.accept()
    device = DeviceCommunicator(websocket, client_id)
    device_connections[client_id] = device

    try:
        while True:
            message = await websocket.receive_text()
            data = json.loads(message)

            if data.get("action") == "connect":
                protocol = data.get("protocol", "tcp").lower()
                ip_address = data.get("ip_address")
                port = int(data.get("port", 5000 if protocol == "tcp" else 80))

                if device.running:
                    device.running = False
                    await asyncio.sleep(0.5) # Give it a moment to stop

                if protocol == "tcp":
                    asyncio.create_task(
                        device.connect_tcp(ip_address, port)
                    )
                elif protocol == "http":
                    path = data.get("path", "/")
                    interval = int(data.get("interval", 5))
                    asyncio.create_task(
                        device.fetch_http(ip_address, port, path, interval)
                    )

            elif data.get("action") == "disconnect":
                device.running = False
                await websocket.send_json(
                    {
                        "type": "disconnected",
                        "client_id": client_id,
                    }
                )

    except WebSocketDisconnect:
        device.running = False
        device_connections.pop(client_id, None)


@app.get("/")
async def get_root():
    return HTMLResponse(HTML_CONTENT)


with open("index.html", "r") as f:
    HTML_CONTENT = f.read()


@app.get("/api/my-ip")
async def get_my_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return {"ip": ip}
    except Exception:
        return {"ip": "127.0.0.1"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)