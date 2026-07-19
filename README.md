# Smart Irrigation System — UPGRADED SETUP GUIDE

## What Changed from Original

| Feature            | Original               | Upgraded                             |
|--------------------|------------------------|--------------------------------------|
| Temperature Source | DHT11/DHT22 on NodeMCU | OpenWeatherMap real-time API (free)  |
| Humidity Source    | DHT11/DHT22 on NodeMCU | OpenWeatherMap real-time API (free)  |
| Soil Moisture      | Hardware Sensor (A0)   | Hardware Sensor (A0) — unchanged     |
| Monitoring         | Only on-demand reads   | Every 8 hours + continuous readings  |
| NodeMCU sends      | temp + hum + soil      | soil_moisture only                   |

---

## Hardware Wiring (Simplified — no DHT sensor needed)

```
NodeMCU         Component
────────         ─────────
D1         →    Relay IN  (controls motor pump)
A0         →    Soil Moisture Sensor OUT (analog)
3V3        →    Soil Sensor VCC
GND        →    Soil Sensor GND + Relay GND
VIN (5V)   →    Relay VCC
```

DHT11/DHT22 is **no longer wired** — remove it from your circuit.

---

## One-Time Setup

### 1. Get Free OpenWeatherMap API Key
1. Go to https://openweathermap.org/api
2. Sign up (free) → "My API Keys" → copy key
3. Free tier = 1,000 calls/day — more than enough

### 2. Configure server.py
Open `server.py` and edit these 3 lines:
```python
OPENWEATHER_API_KEY = "abc123yourkey"   # ← your key
CITY_NAME           = "Karachi"         # ← your city
COUNTRY_CODE        = "PK"              # ← ISO country code
```

### 3. Configure nodemcu_irrigation.ino
Edit these 3 lines in the .ino file:
```cpp
const char* WIFI_SSID     = "YourWiFiName";
const char* WIFI_PASSWORD = "YourWiFiPass";
const char* SERVER_URL    = "http://192.168.1.XXX:5000/predict";
```
Find your PC/laptop IP with:
- Windows: `ipconfig`
- Linux/Mac: `ifconfig`
Look for the IP on your local network (usually 192.168.x.x)

### 4. Install Python dependencies
```bash
pip install -r requirements.txt
```

### 5. Copy model files
Make sure these are in the same folder as server.py:
- motor_classifier.pkl
- duration_regressor.pkl

---

## Running the System

### Start the server (on your laptop/PC):
```bash
python server.py
```

### Upload the .ino to NodeMCU:
- Open Arduino IDE
- Install board: ESP8266 (if not already)
- Select board: NodeMCU 1.0 (ESP-12E Module)
- Upload nodemcu_irrigation.ino

---

## API Endpoints

| Endpoint              | Method | Description                              |
|-----------------------|--------|------------------------------------------|
| /predict              | POST   | NodeMCU sends soil_moisture, gets command |
| /weather              | GET    | Current OpenWeatherMap data              |
| /log                  | GET    | All prediction history (last 500)        |
| /monitor              | GET    | 8-hour scheduled check results           |
| /monitor/trigger      | POST   | Manually run an 8-hour check now         |
| /status               | GET    | Server health + next check time          |

---

## How 8-Hour Monitoring Works

The server automatically runs a plant health check every 8 hours:
1. Fetches fresh temperature & humidity from OpenWeatherMap
2. Uses the **most recently received** soil moisture from NodeMCU
3. Runs the ML model
4. Stores result in `/monitor` log with timestamp

You can view all 8-hour checks at: `http://localhost:5000/monitor`
Force an immediate check: `POST http://localhost:5000/monitor/trigger`

---

## Calibrating Soil Sensor

In the .ino file, adjust these values for your specific sensor:
```cpp
#define SOIL_RAW_DRY  850   // raw value when probe in dry air
#define SOIL_RAW_WET  350   // raw value when probe in water
```
Test in Serial Monitor — stick probe in dry soil vs wet soil and note the raw values.
