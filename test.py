# import soundcard as sc
# import soundfile as sf

# OUTPUT_FILE_NAME = "out.wav"    # file name
# SAMPLE_RATE = 48000             # Hz, CD quality
# RECORD_SEC = 5                  # duration in seconds

# # Grab your default speaker but request loopback mode (captures "what you hear")
# with sc.get_microphone(id=str(sc.default_speaker().name), include_loopback=True).recorder(samplerate=SAMPLE_RATE) as mic:
#     # Record from the speaker output
#     data = mic.record(numframes=SAMPLE_RATE * RECORD_SEC)
    
#     # Save as WAV (stereo → left channel only)
#     sf.write(file=OUTPUT_FILE_NAME, data=data[:, 0], samplerate=SAMPLE_RATE)

import asyncio
import websockets

async def test():
    async with websockets.connect("ws://localhost:8765") as ws:
        print("Connected to subtitle server ✅")
        try:
            while True:
                msg = await ws.recv()
                print("Subtitle:", msg)
        except websockets.exceptions.ConnectionClosed:
            print("Server disconnected ❌")

asyncio.run(test())
