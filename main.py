import soundcard as sc
import numpy as np
import whisper
import torch
import queue
import threading
import time
import asyncio
import websockets

# -------------------
# Settings
# -------------------
MODEL_NAME = "tiny.en"   # fastest, use "base.en" or bigger for better accuracy
SAMPLE_RATE = 16000
CHUNK_SEC = 2            # record 2 seconds at a time (more stable)
OVERLAP = 1.0            # overlap to reduce cut words
WS_PORT = 8765           # WebSocket port

# -------------------
# Load Whisper
# -------------------
print("🔄 Loading Whisper model...")
device = "cuda" if torch.cuda.is_available() else "cpu"
model = whisper.load_model(MODEL_NAME, device=device)
print(f"✅ Whisper model '{MODEL_NAME}' ready on {device}")

# -------------------
# Audio Setup
# -------------------
default_speaker = sc.default_speaker()
default_mic = sc.get_microphone(id=str(default_speaker.name), include_loopback=True)

print(f"\n🔊 Capturing system audio from: {default_mic.name}")
print("🎙️ Streaming… press CTRL+C to stop.\n")

# Buffers - CHANGED: current_subtitle instead of queue
audio_queue = queue.Queue()
current_subtitle = ""  # Single current subtitle, no queue
last_subtitle_time = 0

# -------------------
# Recording Thread
# -------------------
def record_audio():
    with default_mic.recorder(samplerate=SAMPLE_RATE) as mic:
        while True:
            data = mic.record(numframes=int(CHUNK_SEC * SAMPLE_RATE))
            audio_queue.put(data)

# -------------------
# Transcription Thread - FASTER processing with better filtering
# -------------------
def transcribe_audio():
    global current_subtitle, last_subtitle_time
    buffer = np.zeros(int((CHUNK_SEC + OVERLAP) * SAMPLE_RATE), dtype=np.float32)
    last_text = ""

    while True: 
        new_chunk = audio_queue.get()
        buffer = np.roll(buffer, -len(new_chunk))
        buffer[-len(new_chunk):] = new_chunk[:, 0]  # take left channel

        # Skip if audio is too quiet (efficiency boost)
        if np.max(np.abs(buffer)) < 0.01:
            continue

        # Run Whisper with better settings for speed
        result = model.transcribe(
            buffer, 
            fp16=False, 
            language="en", 
            verbose=False,
            no_speech_threshold=0.6,  # Higher threshold = less false positives
            condition_on_previous_text=False  # Prevents repetition
        )
        text = result["text"].strip()
        
        # Better filtering: minimum length and no repetition
        if text and text != last_text and len(text) > 5:
            current_subtitle = text
            last_text = text
            last_subtitle_time = time.time()
            print("📝 Subtitle:", current_subtitle)

# -------------------
# Clear subtitles after silence - ONLY clear after real silence, not between words
# -------------------
def clear_old_subtitles():
    global current_subtitle, last_subtitle_time
    while True:
        # Only clear after longer silence (2.5 seconds) and only if no new audio
        if current_subtitle and time.time() - last_subtitle_time > 2.5:
            # Check if there's still audio processing happening
            if audio_queue.empty():  # No pending audio to process
                current_subtitle = ""
                print("🔇 Cleared subtitle after silence")
        time.sleep(0.5)

# -------------------
# WebSocket Server - SEAMLESS: direct replacement, only clear after real silence
# -------------------
async def subtitle_server(websocket):
    last_sent = ""  # Track what we last sent to this client
    
    try:
        while True:
            current_to_send = current_subtitle  # Always send current subtitle directly
            
            # Only send if different from last sent
            if current_to_send != last_sent:
                await websocket.send(current_to_send)
                last_sent = current_to_send
                if current_to_send:
                    print(f"📤 Sent to client: {current_to_send}")
                else:
                    print("📤 Sent clear to client")
            
            await asyncio.sleep(0.1)  # Check every 0.1s but only send when changed
    except websockets.ConnectionClosed:
        print("❌ A client disconnected")
        
def start_ws_server():
    async def run_server():
        async with websockets.serve(subtitle_server, "localhost", WS_PORT):
            print(f"🌐 WebSocket server started on ws://localhost:{WS_PORT}")
            await asyncio.Future()  # run forever

    asyncio.run(run_server())

# -------------------
# Run - ADDED: clear thread
# -------------------
rec_thread = threading.Thread(target=record_audio, daemon=True)
rec_thread.start()

trans_thread = threading.Thread(target=transcribe_audio, daemon=True)
trans_thread.start()

clear_thread = threading.Thread(target=clear_old_subtitles, daemon=True)
clear_thread.start()

ws_thread = threading.Thread(target=start_ws_server, daemon=True)
ws_thread.start()

try:
    while True:
        time.sleep(1)  # keep main thread alive
except KeyboardInterrupt:
    print("\n🛑 Stopping…")
    exit(0)