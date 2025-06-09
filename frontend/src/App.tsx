// frontend/src/App.tsx
import React, { useState, useEffect } from 'react';
import {
  Thermometer,
  Droplets,
  Wind,
  Sprout,
  Power,
  MessageSquare,
  Sun,
  X,
  Send,
  RefreshCw,
  Camera,
  Maximize2,
} from 'lucide-react';

/* ------------------------------------------------------------------ */
/* 1) Types returned by FastAPI                                        */
/* ------------------------------------------------------------------ */
interface SensorReading {
  temperature_c: number;
  mq135_raw: number;
  mq135_pct: number;
  soil_raw: number;
  timestamp: number;
}

interface ActuatorState {
  fan: 'on' | 'off';
  light: 'on' | 'off';
  pump: 'on' | 'off';
}

/* ------------------------------------------------------------------ */
/* 2) Initial placeholders                                             */
/* ------------------------------------------------------------------ */
const initialSensorData = {
  temperature: 0,
  airquality: 0,
  soilMoisture: 0,
  co2: 0,
};

function App() {
  /* ------------- State ------------- */
  const [sensorData, setSensorData] = useState(initialSensorData);
  const [isFanOn, setIsFanOn] = useState(false);
  const [isPumpOn, setIsPumpOn] = useState(false);
  const [isLightOn, setIsLightOn] = useState(false);
  const [isChatOpen, setIsChatOpen] = useState(false);
  const [messages, setMessages] =
    useState<{ text: string; isUser: boolean }[]>([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isUpdating, setIsUpdating] = useState(false);
  const [isCapturingImage, setIsCapturingImage] = useState(false);
  const [isImageExpanded, setIsImageExpanded] = useState(false);

  const baseURL =
    import.meta.env.VITE_API_URL?.toString() ?? 'http://localhost:8000';

  /* ------------------------------------------------------------------ */
  /* 3) Fetch latest snapshot from FastAPI (sensors + actuators)        */
  /* ------------------------------------------------------------------ */
  const handleUpdateData = async () => {
    try {
      setIsUpdating(true);

      /* ---------- sensors ---------- */
      const sensRes = await fetch(`${baseURL}/sensor`);
      if (!sensRes.ok) throw new Error(`HTTP ${sensRes.status}`);
      const data: SensorReading = await sensRes.json();
      setSensorData({
        temperature: Number(data.temperature_c.toFixed(1)),
        airquality: data.mq135_pct,
        soilMoisture: data.soil_raw,
        co2: data.mq135_raw,
      });

      /* ---------- actuators -------- */
      const actRes = await fetch(`${baseURL}/actuators`);
      if (actRes.ok) {
        const act: ActuatorState = await actRes.json();
        setIsFanOn(act.fan === 'on');
        setIsLightOn(act.light === 'on');
        setIsPumpOn(act.pump === 'on');
      }
    } catch (err) {
      console.error('Update failed:', err);
      alert('Could not fetch data. Check the console for details.');
    } finally {
      setIsUpdating(false);
    }
  };

  /* ------------------------------------------------------------------ */
  /* 4) Auto-poll sensors + actuators every 3 s                         */
  /* ------------------------------------------------------------------ */
  useEffect(() => {
    handleUpdateData();                 // immediate first load
    const id = setInterval(handleUpdateData, 60_000);
    return () => clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [baseURL]);

  /* ------------------------------------------------------------------ */
  /* 5) WebSocket – live actuator state (real-time push)                */
  /* ------------------------------------------------------------------ */
  useEffect(() => {
    const protocol = baseURL.startsWith('https') ? 'wss' : 'ws';
    const wsURL = baseURL.replace(/^https?/, protocol) + '/ws/actuators';
    const ws = new WebSocket(wsURL);

    ws.onmessage = event => {
      try {
        const act: ActuatorState = JSON.parse(event.data);
        setIsFanOn(act.fan === 'on');
        setIsLightOn(act.light === 'on');
        setIsPumpOn(act.pump === 'on');
      } catch (err) {
        console.error('Bad WS payload:', err);
      }
    };

    ws.onerror = console.error;
    return () => ws.close();
  }, [baseURL]);

  /* ------------------------------------------------------------------ */
  /* 6) Chat handler                                                    */
  /* ------------------------------------------------------------------ */
/* 6) Chat handler */
const handleSendMessage = async (e: React.FormEvent) => {
  e.preventDefault();
  const trimmed = inputMessage.trim();
  if (!trimmed) return;

  // ➊ Mesajı hemen ekrana yaz
  setMessages(prev => [...prev, { text: trimmed, isUser: true }]);
  setInputMessage('');

  // ➋ API çağrısı
  try {
    const res = await fetch(`${baseURL}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message: trimmed,
        history: messages.map(m => ({
          role: m.isUser ? 'user' : 'assistant',
          content: m.text,
        })),
      }),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json() as { reply: string; history: any[] };

    // ➌ Cevabı ekle
    setMessages(prev => [...prev, { text: data.reply, isUser: false }]);
  } catch (err) {
    console.error('Chat failed:', err);
    setMessages(prev => [...prev, {
      text: 'Sorry, I could not reach the AI service.',
      isUser: false,
    }]);
  }
};

  /* ------------------------------------------------------------------ */
  /* 7) Image capture mock                                              */
  /* ------------------------------------------------------------------ */
  const handleCaptureImage = async () => {
    setIsCapturingImage(true);
    setTimeout(() => setIsCapturingImage(false), 1500);
  };

  /* ------------------------------------------------------------------ */
  /* 8) Render UI                                                       */
  /* ------------------------------------------------------------------ */
  return (
    <div className="min-h-screen bg-gradient-to-br from-green-50 to-white">
      <div className="container mx-auto px-4 py-8">
        <h1 className="text-4xl font-bold text-green-800 mb-8 text-center">
          Smart Plant Growbox
        </h1>

        {/* ------------------ Sensor Dashboard ------------------ */}
        <div className="relative mb-16">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {/* Temperature */}
            <div className="bg-white rounded-xl p-6 shadow-lg">
              <div className="flex items-center gap-4">
                <Thermometer className="w-8 h-8 text-green-600" />
                <div>
                  <p className="text-gray-600">Temperature</p>
                  <p className="text-2xl font-semibold">
                    {sensorData.temperature}°C
                  </p>
                </div>
              </div>
            </div>

            {/* Air Quality */}
            <div className="bg-white rounded-xl p-6 shadow-lg">
              <div className="flex items-center gap-4">
                <Droplets className="w-8 h-8 text-green-600" />
                <div>
                  <p className="text-gray-600">Air Quality</p>
                  <p className="text-2xl font-semibold">
                    {sensorData.airquality}%
                  </p>
                </div>
              </div>
            </div>

            {/* Soil Moisture */}
            <div className="bg-white rounded-xl p-6 shadow-lg">
              <div className="flex items-center gap-4">
                <Sprout className="w-8 h-8 text-green-600" />
                <div>
                  <p className="text-gray-600">Soil Moisture</p>
                  <p className="text-2xl font-semibold">
                    {sensorData.soilMoisture} ppm
                  </p>
                </div>
              </div>
            </div>

            {/* Chat launcher */}
            <div
              className="bg-white rounded-xl p-6 shadow-lg cursor-pointer transition-transform hover:scale-105"
              onClick={() => setIsChatOpen(true)}
            >
              <div className="flex items-center gap-4">
                <MessageSquare className="w-8 h-8 text-green-600" />
                <div>
                  <p className="text-gray-600">Talk to My Plant</p>
                  <p className="text-sm text-green-600">Click to chat</p>
                </div>
              </div>
            </div>
          </div>

          {/* Update Data Button */}
          <button
            onClick={handleUpdateData}
            disabled={isUpdating}
            className="absolute -bottom-12 left-1/2 transform -translate-x-1/2 bg-white text-green-600 px-6 py-2 rounded-lg shadow-md hover:shadow-lg transition-all flex items-center gap-2 disabled:opacity-50"
          >
            <RefreshCw
              className={`w-4 h-4 ${isUpdating ? 'animate-spin' : ''}`}
            />
            {isUpdating ? 'Updating…' : 'Update Data'}
          </button>
        </div>

        {/* ------------------ Main Content ------------------ */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Control Panel */}
          <div className="bg-white rounded-xl p-8 shadow-lg">
            <h2 className="text-2xl font-semibold text-green-800 mb-6">
              Control Panel
            </h2>
            <div className="space-y-8">
              {/* Fan */}
              <div className="flex flex-col gap-4">
                <div
                  className={`w-full py-4 px-6 rounded-lg flex items-center justify-center gap-3 ${
                    isFanOn
                      ? 'bg-green-600 text-white'
                      : 'bg-gray-100 text-gray-600'
                  }`}
                >
                  <Wind className="w-6 h-6" />
                  Fan {isFanOn ? 'ON' : 'OFF'}
                </div>
              </div>

              {/* Pump */}
              <div className="flex flex-col gap-4">
                <div
                  className={`w-full py-4 px-6 rounded-lg flex items-center justify-center gap-3 ${
                    isPumpOn
                      ? 'bg-green-600 text-white'
                      : 'bg-gray-100 text-gray-600'
                  }`}
                >
                  <Power className="w-6 h-6" />
                  Water Pump {isPumpOn ? 'ON' : 'OFF'}
                </div>
              </div>

              {/* Grow Light */}
              <div className="flex flex-col gap-4">
                <div
                  className={`w-full py-4 px-6 rounded-lg flex items-center justify-center gap-3 ${
                    isLightOn
                      ? 'bg-green-600 text-white'
                      : 'bg-gray-100 text-gray-600'
                  }`}
                >
                  <Sun className="w-6 h-6" />
                  Grow Light {isLightOn ? 'ON' : 'OFF'}
                </div>
              </div>
            </div>
          </div>

          {/* Live Plant View */}
          <div className="bg-white rounded-xl p-8 shadow-lg">
            <div className="flex justify-between items-center mb-6">
              <h2 className="text-2xl font-semibold text-green-800">
                Live Plant View
              </h2>
              <button
                onClick={handleCaptureImage}
                disabled={isCapturingImage}
                className="bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700 transition-colors flex items-center gap-2 disabled:opacity-50"
              >
                <Camera className="w-4 h-4" />
                {isCapturingImage ? 'Capturing…' : 'Take New Picture'}
              </button>
            </div>
            <div
              className="aspect-video bg-gray-100 rounded-lg overflow-hidden relative cursor-pointer group"
              onClick={() => setIsImageExpanded(true)}
            >
              <img
                src="https://images.unsplash.com/photo-1416879595882-3373a0480b5b?auto=format&fit=crop&w=1200&q=80"
                alt="Plant live view"
                className="w-full h-full object-cover transition-transform group-hover:scale-105"
              />
              <div className="absolute inset-0 bg-black bg-opacity-0 group-hover:bg-opacity-20 transition-all flex items-center justify-center">
                <Maximize2 className="w-8 h-8 text-white opacity-0 group-hover:opacity-100 transition-opacity" />
              </div>
            </div>
          </div>
        </div>

        {/* ------------------ Expanded Image Modal ------------------ */}
        {isImageExpanded && (
          <div
            className="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center p-4 z-50"
            onClick={() => setIsImageExpanded(false)}
          >
            <div className="relative max-w-5xl w-full">
              <img
                src="https://images.unsplash.com/photo-1416879595882-3373a0480b5b?auto=format&fit=crop&w=1920&q=100"
                alt="Plant live view expanded"
                className="w-full rounded-lg"
                onClick={e => e.stopPropagation()}
              />
              <button
                onClick={() => setIsImageExpanded(false)}
                className="absolute top-4 right-4 p-2 bg-black bg-opacity-50 rounded-full text-white hover:bg-opacity-75 transition-all"
              >
                <X className="w-6 h-6" />
              </button>
            </div>
          </div>
        )}

        {/* ------------------ Chat Window ------------------ */}
        {isChatOpen && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-40">
            <div className="bg-white rounded-xl w-full max-w-2xl h-[600px] flex flex-col">
              {/* Header */}
              <div className="p-4 border-b flex justify-between items-center">
                <h3 className="text-xl font-semibold text-green-800">
                  Talk to Your Plant
                </h3>
                <button
                  onClick={() => setIsChatOpen(false)}
                  className="p-2 hover:bg-gray-100 rounded-full"
                >
                  <X className="w-6 h-6" />
                </button>
              </div>

              {/* Messages */}
              <div className="flex-1 overflow-y-auto p-4 space-y-4">
                {messages.map((message, index) => (
                  <div
                    key={index}
                    className={`flex ${
                      message.isUser ? 'justify-end' : 'justify-start'
                    }`}
                  >
                    <div
                      className={`max-w-[80%] p-4 rounded-xl ${
                        message.isUser
                          ? 'bg-green-600 text-white rounded-br-none'
                          : 'bg-gray-100 text-gray-800 rounded-bl-none'
                      }`}
                    >
                      {message.text}
                    </div>
                  </div>
                ))}
              </div>

              {/* Input */}
              <form onSubmit={handleSendMessage} className="p-4 border-t">
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={inputMessage}
                    onChange={e => setInputMessage(e.target.value)}
                    placeholder="Ask about your plant..."
                    className="flex-1 px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-green-600"
                  />
                  <button
                    type="submit"
                    className="bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700 transition-colors"
                  >
                    <Send className="w-5 h-5" />
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;
