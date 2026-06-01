# Python IPC worker for faster-whisper: reads length-prefixed int16 PCM from stdin,
# transcribes/translates using faster-whisper, writes newline-delimited JSON to stdout.
import sys
import struct
import time
import json
import numpy as np
import warnings

warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=RuntimeWarning)

from faster_whisper import WhisperModel
import torch

# Configuration
MODEL_NAME = "tiny.en"
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
COMPUTE_TYPE = "float16" if DEVICE == "cuda" else "int8"
TASK = "translate"  # "transcribe" for transcription, "translate" to translate any language to English

# initialize model once
print(f"[python] Loading faster-whisper '{MODEL_NAME}' on {DEVICE} (compute_type={COMPUTE_TYPE})...", flush=True)
model = WhisperModel(MODEL_NAME, device=DEVICE, compute_type=COMPUTE_TYPE)
print("[python] Model ready", flush=True)
print(f"[python] Mode: {TASK.upper()}" + (" (translates any language to English)" if TASK == "translate" else ""), flush=True)

def read_exact(fd, n):
    data = b''
    while len(data) < n:
        chunk = sys.stdin.buffer.read(n - len(data))
        if not chunk:
            return None
        data += chunk
    return data

# loop: read 8-byte length (uint64 little-endian), then read that many bytes => int16 LE PCM
while True:
    # read 8 byte header
    hdr = read_exact(sys.stdin.buffer, 8)
    if hdr is None:
        break
    (length,) = struct.unpack('<Q', hdr)
    if length == 0:
        continue
    data = read_exact(sys.stdin.buffer, length)
    if data is None:
        break
    t_recv = time.time()
    # convert bytes -> int16 -> float32 (-1..1)
    arr = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32767.0
    # faster-whisper expects either 1d float32 numpy or file; pass arr
    t0 = time.time()
    try:
        language = "en" if TASK == "transcribe" else None
        segments, info = model.transcribe(arr, language=language, task=TASK, beam_size=1)
        t1 = time.time()
        text = "".join([seg.text for seg in segments]).strip()
    except Exception as e:
        text = ""
        t1 = time.time()
        print(json.dumps({"error": str(e)}), flush=True)
        continue
    out = {
        "text": text,
        "task": TASK,
        "queue_time": t0 - t_recv,
        "infer_time": t1 - t0,
        "timestamp": t_recv
    }
    print(json.dumps(out, ensure_ascii=False), flush=True)
# exit
sys.exit(0)
