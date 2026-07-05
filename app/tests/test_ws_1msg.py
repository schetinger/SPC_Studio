import asyncio
import websockets
import json
import time

async def test():
    uri = "wss://spc-studio.onrender.com/ws/esp/"
    async with websockets.connect(uri, extra_headers={"Origin": "https://spc-studio.onrender.com"}) as ws:
        print("Connected!")
        await asyncio.sleep(2)
        print("Sending message at 2s")
        start = time.time()
        await ws.send(json.dumps({"ping": True}))
        try:
            res = await asyncio.wait_for(ws.recv(), timeout=2)
            print(f"Received in {time.time() - start:.2f}s:", res)
        except Exception as e:
            print("Error type:", type(e).__name__)
        
        print("Waiting for connection to drop...")
        try:
            await ws.recv()
        except Exception as e:
            print(f"Connection dropped at {time.time() - start:.2f}s after sending: {e}")

asyncio.run(test())
