# -*- coding: utf-8 -*-
import sys
import io
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
TASK = "translate"      # "transcribe" for transcription, "translate" to translate any language to English

# -------------------
# Load Whisper
# -------------------
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
print("🔄 Loading Whisper model...")
device = "cuda" if torch.cuda.is_available() else "cpu"
model = whisper.load_model(MODEL_NAME, device=device)
print(f"✅ Whisper model '{MODEL_NAME}' ready on {device}")
print(f"🔄 Mode: {TASK.upper()}" + (" (translates any language to English)" if TASK == "translate" else ""))

# Buffers - CHANGED: current_subtitle instead of queue
audio_queue = queue.Queue()
current_subtitle = ""  # Single current subtitle, no queue
last_subtitle_time = 0

# benchmark counters
_total_infers = 0
_sum_queue_delay = 0.0
_sum_infer_time = 0.0
_last_bench_report = time.time()
_BENCH_INTERVAL = 10.0  # seconds

# -------------------
# Audio Setup
# -------------------
default_speaker = sc.default_speaker()
default_mic = sc.get_microphone(id=str(default_speaker.name), include_loopback=True)

print(f"\n🔊 Capturing system audio from: {default_mic.name}")
print("🎙️ Streaming… press CTRL+C to stop.\n")

# -------------------
# Recording Thread
# -------------------
def record_audio():
    with default_mic.recorder(samplerate=SAMPLE_RATE) as mic:
        while True:
            data = mic.record(numframes=int(CHUNK_SEC * SAMPLE_RATE))
            audio_queue.put((time.time(), data))

# -------------------
# Transcription Thread - FASTER processing with better filtering
# -------------------
def transcribe_audio():
    global current_subtitle, last_subtitle_time, _total_infers, _sum_queue_delay, _sum_infer_time, _last_bench_report
    buffer = np.zeros(int((CHUNK_SEC + OVERLAP) * SAMPLE_RATE), dtype=np.float32)
    last_text = ""

    while True:
        timestamp, new_chunk = audio_queue.get()
        queue_delay = time.time() - timestamp

        buffer = np.roll(buffer, -len(new_chunk))
        buffer[-len(new_chunk):] = new_chunk[:, 0]  # take left channel

        # Skip if audio is too quiet (efficiency boost)
        if np.max(np.abs(buffer)) < 0.01:
            continue

        t0 = time.time()
        result = model.transcribe(
            buffer,
            fp16=False,
            language="en" if TASK == "transcribe" else None,
            task=TASK,
            verbose=False,
            no_speech_threshold=0.6,
            condition_on_previous_text=False
        )
        t1 = time.time()

        infer_time = t1 - t0
        _total_infers += 1
        _sum_queue_delay += queue_delay
        _sum_infer_time += infer_time

        text = result["text"].strip()

        # Better filtering: minimum length and no repetition
        if text and text != last_text and len(text) > 5:
            current_subtitle = text
            last_text = text
            last_subtitle_time = time.time()
            print(f"📝 Subtitle: {current_subtitle}  [queue_delay={queue_delay:.3f}s infer={infer_time:.3f}s]", flush=True)

        now = time.time()
        if now - _last_bench_report >= _BENCH_INTERVAL and _total_infers > 0:
            avg_queue = _sum_queue_delay / _total_infers
            avg_infer = _sum_infer_time / _total_infers
            print(f"[python][BENCH] total_inf={_total_infers} avg_queue={avg_queue:.3f}s avg_infer={avg_infer:.3f}s", flush=True)
            _total_infers = 0
            _sum_queue_delay = 0.0
            _sum_infer_time = 0.0
            _last_bench_report = now

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
            print(f"🌐 WebSocket server started on ws://localhost:{WS_PORT}", flush=True)
            print("PY_READY: WS_READY", flush=True)
            await asyncio.Future()  # run forever

    asyncio.run(run_server())

# log device / GPU info
print(f"runtime device={device}", flush=True)
if torch.cuda.is_available():
    try:
        print(f"GPU count={torch.cuda.device_count()}, GPU name={torch.cuda.get_device_name(0)}", flush=True)
    except Exception as e:
        print(f"GPU info error: {e}", flush=True)
else:
    print("CUDA not available — running on CPU", flush=True)

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
