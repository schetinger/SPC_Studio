import asyncio
import websockets
import time

async def test():
    uri = "wss://spc-studio.onrender.com/ws/esp/"
    start = time.time()
    try:
        async with websockets.connect(uri, extra_headers={"Origin": "https://spc-studio.onrender.com"}) as ws:
            print("Connected at", time.time() - start)
            await ws.recv() # Wait for the connection to drop
    except Exception as e:
        print("Dropped at", time.time() - start, "seconds with error:", e)

asyncio.run(test())
