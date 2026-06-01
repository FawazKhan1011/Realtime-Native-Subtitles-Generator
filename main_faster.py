import sys
import io
import time
import queue
import threading
import warnings

import numpy as np
import soundcard as sc
import torch
from faster_whisper import WhisperModel
import asyncio
import websockets

warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=RuntimeWarning)

# === CONFIGURATION ===
SAMPLE_RATE = 16000
CHUNK_SEC = 2           # record 2s chunks (match main.py for fair comparison)
OVERLAP = 1.0           # overlap to reduce cut words
MODEL_NAME = "base"  # use "base" / "base.en" / "tiny.en" etc.
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
COMPUTE_TYPE = "float16" if DEVICE == "cuda" else "int8"
WS_PORT = 8765
TASK = "translate"      # "transcribe" for transcription, "translate" to translate any language to English

# === SETUP STDOUT ENCODING (like main.py) ===
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

print(f"[python] Loading faster-whisper '{MODEL_NAME}' on {DEVICE} (compute_type={COMPUTE_TYPE})...")
model = WhisperModel(MODEL_NAME, device=DEVICE, compute_type=COMPUTE_TYPE) 
print("[python] Model ready.")
print(f"[python] Mode: {TASK.upper()}" + (" (translates any language to English)" if TASK == "translate" else ""))

# audio device (loopback)
speaker = sc.default_speaker()
mic = sc.get_microphone(id=str(speaker.name), include_loopback=True)
print(f"[python] Capturing system audio from: {mic.name}")
print("🎙️ Streaming… press CTRL+C to stop.\n")

# shared state
# audio queue: now store (timestamp, frames) so we can measure queue delay
audio_queue = queue.Queue()
current_subtitle = ""
last_subtitle_time = 0.0

# simple benchmark counters
_total_infers = 0
_sum_queue_delay = 0.0
_sum_infer_time = 0.0
_last_bench_report = time.time()
_BENCH_INTERVAL = 10.0  # seconds

# === RECORDING THREAD ===
def record_audio():
    with mic.recorder(samplerate=SAMPLE_RATE) as recorder:
        while True:
            data = recorder.record(numframes=int(CHUNK_SEC * SAMPLE_RATE))
            audio_queue.put((time.time(), data))
            # minimal heartbeat so stdout flushes
            # print(".", end="", flush=True)

# === TRANSCRIBE THREAD (using faster-whisper) ===
def transcribe_audio():
    global current_subtitle, last_subtitle_time, _total_infers, _sum_queue_delay, _sum_infer_time, _last_bench_report
    buf_len = int((CHUNK_SEC + OVERLAP) * SAMPLE_RATE)
    buffer = np.zeros(buf_len, dtype=np.float32)
    last_text = ""

    while True:
        timestamp, frames = audio_queue.get()
        queue_delay = time.time() - timestamp

        n = frames.shape[0]
        buffer = np.roll(buffer, -n)
        buffer[-n:] = frames[:, 0].astype(np.float32)

        # quick VAD: skip very quiet audio
        if np.max(np.abs(buffer)) < 0.01:
            continue

        try:
            t0 = time.time()
            # faster-whisper: returns segments (iterable) and info
            segments, _ = model.transcribe(buffer, beam_size=1, language= None if TASK == "transcribe" else None, task=TASK)
            t1 = time.time()
            infer_time = t1 - t0

            _total_infers += 1
            _sum_queue_delay += queue_delay
            _sum_infer_time += infer_time

            text = "".join([seg.text for seg in segments]).strip()

            # filtering: avoid tiny results and repetition
            if text and text != last_text and len(text) > 3:
                current_subtitle = text
                last_text = text
                last_subtitle_time = time.time()
                print(f"📝 Subtitle: {current_subtitle}  [queue_delay={queue_delay:.3f}s infer={infer_time:.3f}s]", flush=True)

            # periodic benchmark report
            now = time.time()
            if now - _last_bench_report >= _BENCH_INTERVAL and _total_infers > 0:
                avg_queue = _sum_queue_delay / _total_infers
                avg_infer = _sum_infer_time / _total_infers
                print(f"[python][BENCH] total_inf={_total_infers} avg_queue={avg_queue:.3f}s avg_infer={avg_infer:.3f}s", flush=True)
                # reset counters
                _total_infers = 0
                _sum_queue_delay = 0.0
                _sum_infer_time = 0.0
                _last_bench_report = now

        except Exception as e:
            print("[Transcribe Error]", e, flush=True)
            time.sleep(0.1)

# === CLEAR AFTER SILENCE ===
def clear_old_subtitles():
    global current_subtitle, last_subtitle_time
    while True:
        if current_subtitle and time.time() - last_subtitle_time > 2.5:
            # if queue has no pending audio, clear (avoid clearing mid-processing)
            if audio_queue.empty():
                current_subtitle = ""
                print("🔇 Cleared subtitle after silence")
        time.sleep(0.5)

# === WEBSOCKET SERVER (same API as main.py) ===
async def subtitle_server(websocket):
    last_sent = ""
    try:
        while True:
            to_send = current_subtitle
            if to_send != last_sent:
                await websocket.send(to_send)
                last_sent = to_send
                if to_send:
                    print(f"📤 Sent to client: {to_send}")
                else:
                    print("📤 Sent clear to client")
            await asyncio.sleep(0.1)
    except websockets.ConnectionClosed:
        print("❌ A client disconnected")

def start_ws_server():
    async def run_server():
        async with websockets.serve(subtitle_server, "localhost", WS_PORT):
            print(f"🌐 WebSocket server started on ws://localhost:{WS_PORT}", flush=True)
            # readiness token for Electron to detect backend is ready
            print("PY_READY: WS_READY", flush=True)
            await asyncio.Future()
    asyncio.run(run_server())

# log device / GPU info (ensure flush so Electron sees it)
print(f"[python] runtime device={DEVICE}, compute_type={COMPUTE_TYPE}", flush=True)
if torch.cuda.is_available():
    try:
        gpu_count = torch.cuda.device_count()
        gpu_names = [torch.cuda.get_device_name(i) for i in range(gpu_count)]
        print(f"[python] CUDA available: count={gpu_count}, names={gpu_names}", flush=True)
    except Exception as e:
        print(f"[python] CUDA info error: {e}", flush=True)
else:
    print("[python] CUDA not available — running on CPU", flush=True)

# === MAIN ===
if __name__ == "__main__":
    # start threads
    threading.Thread(target=record_audio, daemon=True).start()
    threading.Thread(target=transcribe_audio, daemon=True).start()
    threading.Thread(target=clear_old_subtitles, daemon=True).start()
    threading.Thread(target=start_ws_server, daemon=True).start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[python] Stopping…")
        exit(0)
