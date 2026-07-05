import asyncio
import websockets
import time

async def test():
    uri = "wss://spc-studio.onrender.com/ws/esp/"
    # Disable native keepalive ping
    async with websockets.connect(uri, extra_headers={"Origin": "https://spc-studio.onrender.com"}, ping_interval=None) as ws:
        print("Connected!")
        start = time.time()
        try:
            await ws.recv()
        except Exception as e:
            print(f"Dropped at {time.time() - start:.2f}s")

asyncio.run(test())
