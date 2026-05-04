# RFID Truck Scanner System - Dashboard

This application provides a real-time dashboard for monitoring and managing industrial RFID truck scanners. It supports multiple communication protocols and automatically parses various data formats.

## 🚀 Getting Started

### 1. Prerequisites
- Python 3.8+
- Node.js (optional, for screenshots)

### 2. Install Dependencies
Install the required Python packages:
```bash
pip install -r requirements.txt
```

(Optional) Install Node.js dependencies for the screenshot utility:
```bash
npm install
```

### 3. Run the Application
Start the FastAPI server:
```bash
python main.py
```
The application will be available at [http://localhost:5000](http://localhost:5000).

---

## 🛠 How to Use

### Connecting to a Scanner
1. Open the dashboard in your browser.
2. **Select Protocol**: Choose between **TCP Socket** (for scanners that push data over raw TCP) or **HTTP Polling** (for scanners with a web API).
3. **Enter IP Address**: Provide the network IP of the RFID scanner.
4. **Enter Port**:
   - Default for **TCP**: `5000`
   - Default for **HTTP**: `80`
5. **Path & Interval** (HTTP only): Specify the API endpoint path (e.g., `/api/scan`) and how often to poll.
6. Click **Connect**.

### Viewing Data
Once connected, the status indicator will turn green. Any data received from the scanner will appear instantly in the "Live Data Feed". The system automatically parses:
- **JSON**: `{"rfid": "123", "vehicle": "ABC"}`
- **CSV**: `123, ABC`
- **Key=Value**: `rfid=123 vehicle=ABC`
- **Plain Text**: Raw string fallback.

---

## ⚙️ Configuration Points

### Server Port
By default, the dashboard runs on port `5000`. You can change this at the bottom of `main.py`:
```python
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000) # Change 5000 to your preferred port
```

### Scanner Identification
The system identifies data sources primarily by their **IP Address**. This ensures that in multi-gate environments, every scan is accurately attributed to the correct physical location without relying on easily-spoofed internal IDs.

---

## 📸 Utilities
To capture a screenshot of the live dashboard (useful for reports):
```bash
node screenshot.mjs http://localhost:5000 "my-scan-report"
```
This will save a file named `screenshot-my-scan-report.png`.
