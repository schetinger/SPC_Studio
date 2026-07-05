import asyncio
import websockets
import json

async def test():
    uri = "wss://spc-studio.onrender.com/ws/esp/"
    async with websockets.connect(uri, extra_headers={"Origin": "https://spc-studio.onrender.com"}) as ws:
        print("Connected!")
        await asyncio.sleep(8)
        print("Sent ping at 8s")
        await ws.send(json.dumps({"ping": True}))
        try:
            res = await asyncio.wait_for(ws.recv(), timeout=5)
            print("Received:", res)
        except Exception as e:
            print("Error receiving:", type(e).__name__)

asyncio.run(test())
