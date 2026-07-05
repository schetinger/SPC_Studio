import asyncio
import websockets
import json

async def test():
    uri = "wss://spc-studio.onrender.com/ws/esp/"
    async with websockets.connect(uri, extra_headers={"Origin": "https://spc-studio.onrender.com"}) as ws:
        print("Connected!")
        await ws.send(json.dumps({"ping": True}))
        print("Sent ping")
        try:
            res = await asyncio.wait_for(ws.recv(), timeout=5)
            print("Received:", res)
        except Exception as e:
            print("Error receiving:", e)

asyncio.run(test())
