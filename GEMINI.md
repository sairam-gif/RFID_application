# RFID Truck Scanner System

Industrial RFID truck gate management system for real-time monitoring and control.

## Project Overview
This system manages multiple RFID scanners at facility entry/exit gates. It identifies trucks by their RFID tags, displays information in real-time on a dashboard, and provides controls for gate operations.

## Architecture
- **Scanner Communication**: Python `asyncio` TCP sockets connect to raw TCP scanners.
- **Backend**: FastAPI with WebSocket support for instant data broadcasting.
- **Frontend**: Single-page dashboard using HTML5, Vanilla JavaScript, and Tailwind CSS (via CDN).
- **Data Flow**: Scanner (TCP) -> Python Listener -> WebSocket -> Browser Dashboard.

## Tech Stack
- **Backend**: Python 3.x, FastAPI, Uvicorn, WebSockets.
- **Frontend**: HTML5, Vanilla JS, Tailwind CSS.
- **Tools**: Playwright (for automated screenshots/monitoring).

## Core Principles & Rules
- **Identity**: Scanners are identified **exclusively by their IP address**. Never use IDs or serial numbers as primary keys.
- **Real-time**: Data must flow live from scanner to screen. No page refreshes.
- **Storage**: Currently, the system operates without a database (no storage). Data is live-only.
- **Resilience**: The TCP listener must auto-reconnect on socket drop and never crash on bad data frames.
- **Logging**: Use Python `logging` instead of `print()`. Include `scanner_ip` in every log line.

## Project Structure
- `main.py`: The unified FastAPI server, WebSocket broadcaster, and TCP listener.
- `index.html`: The real-time dashboard frontend.
- `requirements.txt`: Python dependencies.
- `package.json`: Node.js dependencies (primarily for Playwright).
- `screenshot.mjs`: Utility to capture dashboard screenshots.

## Getting Started

### Backend
1. Install dependencies: `pip install -r requirements.txt`
2. Run the server: `python main.py`

### Frontend
- The dashboard is served automatically by `main.py` at `http://localhost:5000`.

### Screenshots
1. Install Node dependencies: `npm install`
2. Run the screenshot script: `node screenshot.mjs`

## Development Conventions
- Adhere to the IP-centric identification for all scanner events.
- Ensure all new data formats are handled by the dynamic parser in `main.py`.
- Keep the frontend build-step free; use CDN-based libraries if needed.
