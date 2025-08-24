import asyncio
import websockets
import datetime

async def subtitle_server(websocket):
    print(f"✅ Client connected: {websocket.remote_address}")
    await websocket.send("[server] connected ✓")

    try:
        # Send some test subtitles every 2s
        subtitles = [
            "Hello 👋",
            "This is a test subtitle",
            "Your WebSocket works!",
            "Soon: Real-time subtitles 🎬"
        ]
        for sub in subtitles:
            await websocket.send(sub)
            await asyncio.sleep(2)

        # Keep alive with heartbeats
        while True:
            msg = f"[server] heartbeat {datetime.datetime.now().strftime('%H:%M:%S')}"
            await websocket.send(msg)
            await asyncio.sleep(2)
    except websockets.exceptions.ConnectionClosed:
        print(f"❌ Client disconnected: {websocket.remote_address}")

async def run_server():
    async with websockets.serve(subtitle_server, "127.0.0.1", 8765):
        print("🌐 WebSocket server started on ws://127.0.0.1:8765")
        await asyncio.Future()  # run forever

def start_ws_server():
    asyncio.run(run_server())

if __name__ == "__main__":
    start_ws_server()
