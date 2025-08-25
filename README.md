# 🎬 YourTitles – A Real-Time Native Subtitle Generator

YourTitles is a desktop application that generates **real-time subtitles for any system audio**.
It works seamlessly with YouTube, video calls, online lectures, movies, music, audio or any media without built-in captions.

Built with **Python (Whisper + SoundCard)** and **Electron.js**, it combines the power of AI speech recognition with a sleek, always-on-top floating window.

---

## 🚀 Introduction

Many videos, meetings, and online streams lack proper subtitles, making them inaccessible for hearing-impaired users, non-native speakers, or multitaskers.
**YourTitles** solves this by providing **instant, real-time subtitles for everything on your system**.

* No need for video-specific captions.
* Works across any platform, app, or browser.
* Designed for accessibility, productivity, and inclusivity.

---

## ✨ Features

* 🎙️ **Real-Time Transcription** using OpenAI Whisper.
* 🔊 **System-Wide Audio Capture** via loopback (not just mic).
* 🌐 **WebSocket Bridge** between Python and Electron frontend.
* 🖼️ **Floating Subtitle Window** – draggable, resizable, transparent, always on top.
* 🟢 **Connection Status Indicator** (connecting / connected).
* ⏱️ **Smart Silence Handling** – clears subtitles when audio stops.
* 📝 **Smart Line Breaking** for readability.

---

## 🛠️ Tech Stack

* **Python** – Whisper (speech-to-text), SoundCard (loopback audio), WebSockets.
* **Electron.js** – Desktop wrapper, floating window, UI controls.
* **HTML + CSS + JS** – Frontend styling & animations.

---

## 📦 Installation & Setup

### 1️⃣ Clone the repository

```bash
git clone https://github.com/your-username/YourTitles.git
cd YourTitles
```

### 2️⃣ Setup Python environment

```bash
python -m venv venv
# Activate venv
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3️⃣ Setup Electron dependencies

```bash
cd electron
npm install
```

### 4️⃣ Run the app

```bash
cd electron
npm start
```

---

## 📂 Project Structure

```
YourTitles/
│── main.py              # Python backend (Whisper transcription + WebSocket)
│── requirements.txt     # Python dependencies
│── electron/            # Electron frontend
│   ├── index.html       # UI for subtitles
│   ├── main.js          # Electron app logic
│   ├── preload.js       # API bridge
│   └── package.json     # Node.js config
│── README.md            # Project documentation
```

---

## 🎥 Demo Video

* link :- https://drive.google.com/file/d/1vjXrYio9Kw5_C5g0tcGNLC_tR28VNiiU/view?usp=sharing

---
## 🎯 Future Scope / Plans

* 🌍 **Multilingual Support** – Support more languages with larger Whisper models.
* 🖥️ **Packaging as EXE/AppImage/Dmg** – One-click install for Windows, Linux, Mac.
* 🎨 **Customizable Themes** – Change font, colors, background transparency.
* 📑 **Subtitle Logging** – Save transcripts to a file for later review.
* 🎥 **Streaming/Caption Overlay** – OBS plugin for live streaming with subtitles.
* 🤝 **Accessibility Features** – Auto-detect spoken language, text-to-speech for translations.

---

## 🤝 Contributing

Pull requests are welcome!
For major changes, please open an issue first to discuss what you’d like to change.

---

## 📜 License

MIT License © 2025 Fawaz Khan
