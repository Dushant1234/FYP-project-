// #include <ESP8266WiFi.h>
// #include <ESP8266HTTPClient.h>
// #include <ArduinoJson.h>

// const char* WIFI_SSID     = "OPPO A54";
// const char* WIFI_PASSWORD = "12345678A";

// // Use your laptop's local IP (from ipconfig)
// const char* SERVER_URL = "http://192.168.78.77:5000/predict";   // ← CHANGE IF IP CHANGES

// #define RELAY_PIN   D1
// #define SOIL_PIN    A0
// #define READ_INTERVAL_MS  10000

// #define RELAY_ON    HIGH     // Change to LOW if motor doesn't turn on
// #define RELAY_OFF   LOW

// #define SOIL_RAW_DRY  850
// #define SOIL_RAW_WET  350

// WiFiClient wifiClient;

// unsigned long lastReadTime = 0;
// unsigned long motorOffTime = 0;
// bool motorRunning = false;

// void setup() {
//   Serial.begin(115200);
//   pinMode(RELAY_PIN, OUTPUT);
//   digitalWrite(RELAY_PIN, RELAY_OFF);

//   WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
//   Serial.print("Connecting to WiFi");
//   while (WiFi.status() != WL_CONNECTED) {
//     delay(500);
//     Serial.print(".");
//   }
//   Serial.println("\nWiFi Connected!");
//   Serial.print("NodeMCU IP: "); Serial.println(WiFi.localIP());
//   Serial.print("Server URL: "); Serial.println(SERVER_URL);
// }

// void loop() {
//   unsigned long now = millis();

//   if (motorRunning && now >= motorOffTime) {
//     digitalWrite(RELAY_PIN, RELAY_OFF);
//     motorRunning = false;
//     Serial.println("[MOTOR] Auto OFF");
//   }

//   if (now - lastReadTime >= READ_INTERVAL_MS) {
//     lastReadTime = now;

//     int soilRaw = analogRead(SOIL_PIN);
//     float soilPct = (float)map(soilRaw, SOIL_RAW_DRY, SOIL_RAW_WET, 0, 100);
//     soilPct = constrain(soilPct, 0, 100);

//     Serial.printf("[SENSOR] Soil=%.1f%% (raw=%d)\n", soilPct, soilRaw);
//     sendToServer(soilPct);
//   }
// }

// void sendToServer(float soilPct) {
//   if (WiFi.status() != WL_CONNECTED) {
//     Serial.println("[WiFi] Disconnected!");
//     return;
//   }

//   HTTPClient http;
//   http.begin(wifiClient, SERVER_URL);
//   http.addHeader("Content-Type", "application/json");
//   http.setTimeout(10000);

//   StaticJsonDocument<64> doc;
//   doc["soil_moisture"] = soilPct;
//   String payload;
//   serializeJson(doc, payload);

//   Serial.print("[HTTP] Sending → ");
//   Serial.println(payload);

//   int httpCode = http.POST(payload);

//   if (httpCode == 200) {
//     String response = http.getString();
//     Serial.print("[Server Response] ");
//     Serial.println(response);

//     StaticJsonDocument<256> resp;
//     DeserializationError err = deserializeJson(resp, response);

//     if (!err) {
//       int motorState = resp["motor_state"];
//       float durationMin = resp["duration_min"];

//       if (motorState == 1 && durationMin > 0) {
//         digitalWrite(RELAY_PIN, RELAY_ON);
//         motorRunning = true;
//         motorOffTime = millis() + (unsigned long)(durationMin * 60 * 1000);
//         Serial.printf("[MOTOR] ON for %.1f minutes\n", durationMin);
//       } else {
//         digitalWrite(RELAY_PIN, RELAY_OFF);
//         motorRunning = false;
//         Serial.println("[MOTOR] OFF");
//       }
//     }
//   } else {
//     Serial.printf("[HTTP Error] Code: %d\n", httpCode);
//   }

//   http.end();
// }
#include <ESP8266WiFi.h>
#include <ESP8266HTTPClient.h>
#include <ArduinoJson.h>

const char* WIFI_SSID     = "OPPO A54";
const char* WIFI_PASSWORD = "12345678A";
const char* SERVER_URL    = "http://192.168.102.77:5000/predict";   // ← Update IP

#define RELAY_PIN   D1
#define SOIL_PIN    A0
#define READ_INTERVAL_MS  10000

#define RELAY_ON    HIGH
#define RELAY_OFF   LOW

WiFiClient wifiClient;

unsigned long lastReadTime = 0;
unsigned long motorOffTime = 0;
bool motorRunning = false;

void setup() {
  Serial.begin(115200);
  pinMode(RELAY_PIN, OUTPUT);
  digitalWrite(RELAY_PIN, RELAY_OFF);

  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi Connected!");
}

void loop() {
  unsigned long now = millis();

  if (motorRunning && now >= motorOffTime) {
    digitalWrite(RELAY_PIN, RELAY_OFF);
    motorRunning = false;
    Serial.println("[MOTOR] Auto OFF");
  }

  if (now - lastReadTime >= READ_INTERVAL_MS) {
    lastReadTime = now;

    int soilRaw = analogRead(SOIL_PIN);
    float soilPct = map(soilRaw, 850, 350, 0, 100);  // Adjust calibration
    soilPct = constrain(soilPct, 0, 100);

    Serial.printf("[SENSOR] Soil=%.1f%%\n", soilPct);
    sendToServer(soilPct);
  }
  delay(100);
}

void sendToServer(float soilPct) {
  if (WiFi.status() != WL_CONNECTED) return;

  HTTPClient http;
  http.begin(wifiClient, SERVER_URL);
  http.addHeader("Content-Type", "application/json");

  StaticJsonDocument<64> doc;
  doc["soil_moisture"] = soilPct;
  String payload;
  serializeJson(doc, payload);

  int httpCode = http.POST(payload);

  if (httpCode == 200) {
    String response = http.getString();
    StaticJsonDocument<512> resp;
    deserializeJson(resp, response);

    int motorState = resp["motor_state"];
    int durationSec = resp["duration_sec"];
    JsonObject burst = resp["burst_info"];

    if (motorState == 1 && durationSec > 0) {
      String mode = burst["mode"];
      if (mode == "burst") {
        runBurst(burst["burst_sec"], burst["pause_sec"], durationSec);
      } else {
        digitalWrite(RELAY_PIN, RELAY_ON);
        motorRunning = true;
        motorOffTime = millis() + (durationSec * 1000UL);
        Serial.printf("[MOTOR] ON for %d sec\n", durationSec);
      }
    } else {
      digitalWrite(RELAY_PIN, RELAY_OFF);
      motorRunning = false;
    }
  }
  http.end();
}

void runBurst(int burstSec, int pauseSec, int totalSec) {
  Serial.println("[MOTOR] Starting Burst Mode");
  int cycles = totalSec / (burstSec + pauseSec) + 1;
  for (int i = 0; i < cycles; i++) {
    digitalWrite(RELAY_PIN, RELAY_ON);
    delay(burstSec * 1000);
    digitalWrite(RELAY_PIN, RELAY_OFF);
    if (i < cycles - 1) delay(pauseSec * 1000);
  }
  Serial.println("[MOTOR] Burst Cycle Completed");
}