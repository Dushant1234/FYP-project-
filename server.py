from flask import Flask, request, jsonify
from flask_cors import CORS
import pickle
import pandas as pd
import requests
import time
import os

app = Flask(__name__)
CORS(app)

# CONFIG
OPENWEATHER_API_KEY = "bcf4f90aa898f3cc27ab53952482278c"
CITY_NAME = "Karachi"
COUNTRY_CODE = "PK"

# Tomato Settings
BASE_OPTIMAL_SOIL = 55
PUMP_RATE_ML_PER_SEC = 167

prediction_log = []
_last_soil_pct = 50.0
_weather_cache = {}
_cache_time = 0

def get_weather():
    global _weather_cache, _cache_time
    now = time.time()
    if _weather_cache and (now - _cache_time) < 120:
        return _weather_cache
    url = f"https://api.openweathermap.org/data/2.5/weather?q={CITY_NAME},{COUNTRY_CODE}&appid={OPENWEATHER_API_KEY}&units=metric"
    try:
        resp = requests.get(url, timeout=5)
        data = resp.json()
        result = {
            "temperature_c": round(data["main"]["temp"], 1),
            "humidity_pct": round(data["main"]["humidity"], 1),
            "weather_desc": data["weather"][0]["description"]
        }
        _weather_cache = result
        _cache_time = now
        return result
    except:
        return {"temperature_c": 28.0, "humidity_pct": 65.0, "weather_desc": "cached"}

def calculate_duration(temp, hum, soil):
    """Use all three values for better decision"""
    # Base duration from soil
    soil_factor = max(0, (BASE_OPTIMAL_SOIL - soil) / 50.0)
    
    # Temperature factor (hotter = more water)
    temp_factor = max(0, (temp - 25) / 20.0)
    
    # Humidity factor (low humidity = more water)
    hum_factor = max(0, (70 - hum) / 50.0)
    
    # Combined factor
    total_factor = (soil_factor * 0.6) + (temp_factor * 0.25) + (hum_factor * 0.15)
    
    water_ml = 200 + (total_factor * 600)   # 200 to 800 ml
    seconds = water_ml / PUMP_RATE_ML_PER_SEC
    return max(2, min(round(seconds), 8))

@app.route('/predict', methods=['POST'])
def predict():
    global _last_soil_pct
    try:
        data = request.get_json(force=True)
        soil = float(data['soil_moisture'])
        _last_soil_pct = soil

        weather = get_weather()
        temp = weather["temperature_c"]
        hum = weather["humidity_pct"]

        # Use all values
        pump_seconds = calculate_duration(temp, hum, soil)
        motor_state = 1 if pump_seconds > 0 and soil < 65 else 0

        message = f"Motor {'ON' if motor_state else 'OFF'} for {pump_seconds} sec (Soil:{soil:.1f} T:{temp} H:{hum})"

        entry = {
            'time': time.strftime('%H:%M:%S'),
            'soil_moisture': soil,
            'temperature': temp,
            'humidity': hum,
            'duration_sec': pump_seconds,
            'message': message
        }
        prediction_log.append(entry)
        if len(prediction_log) > 500:
            prediction_log.pop(0)

        print(message)

        return jsonify({
            'motor_state': motor_state,
            'duration_sec': pump_seconds,
            'message': message,
            'temperature_c': temp,
            'humidity_pct': hum,
            'soil_moisture': soil
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/status', methods=['GET'])
def status():
    return jsonify({'server': 'running', 'last_soil': _last_soil_pct})

@app.route('/log', methods=['GET'])
def get_log():
    return jsonify(prediction_log)

@app.route('/weather', methods=['GET'])
def weather_now():
    return jsonify(get_weather())

if __name__ == '__main__':
    print("✅ Server Running - Using All Values (Soil + Temp + Humidity)")
    app.run(host='0.0.0.0', port=5000, debug=False)