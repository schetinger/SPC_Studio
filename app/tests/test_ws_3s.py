import asyncio
import websockets
import json
import time

async def test():
    uri = "wss://spc-studio.onrender.com/ws/esp/"
    async with websockets.connect(uri, extra_headers={"Origin": "https://spc-studio.onrender.com"}) as ws:
        print("Connected!")
        for i in range(15):
            await asyncio.sleep(3)
            print(f"Sending ping at {i*3 + 3}s")
            start = time.time()
            await ws.send(json.dumps({"ping": True}))
            try:
                res = await asyncio.wait_for(ws.recv(), timeout=2)
                print(f"Received in {time.time() - start:.2f}s:", res)
            except Exception as e:
                print("Error type:", type(e).__name__)
                break
        print("Done!")

asyncio.run(test())
