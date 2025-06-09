# 🌿 Smart Plant Growbox

An AI-powered IoT growbox system designed to monitor and control environmental conditions for plant growth. This project integrates real-time sensor data, actuator control, object detection (YOLO), and a GPT-based chatbot interface to create an intelligent plant assistant.

---

## 🚀 Features

- 🌡️ Monitor temperature, CO2 level (MQ-135), and soil moisture
- 🔦 Control grow light, fan, and water pump (manual & automated)
- 📷 Live camera image capture with YOLO-based strawberry growth stage detection
- 🤖 AI chatbot (GPT) for real-time plant care guidance
- 📈 Web dashboard with auto-updating sensor & actuator status
- 🔌 Raspberry Pi GPIO control with Tasmota device integration
- 🧠 LangChain-powered decision loop with sensor-based actuation

---

## 🧰 Tech Stack

| Layer       | Tech                        |
|-------------|-----------------------------|
| Frontend    | React, TypeScript, Tailwind |
| Backend     | FastAPI, Python             |
| AI Layer    | OpenAI GPT API, LangChain   |
| Image AI    | YOLOv8 (custom pipeline)    |
| Hardware    | Raspberry Pi, DHT22, MQ-135, YL-69, Camera, Relays |
| Realtime    | WebSocket                   |

---

## 🛠️ Installation

### 1. Clone the Project

```bash
git clone https://github.com/yusufkrkmz/smart-growbox.git
cd smart-growbox
