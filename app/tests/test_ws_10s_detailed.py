import asyncio
import websockets
import json
import traceback

async def test():
    uri = "wss://spc-studio.onrender.com/ws/esp/"
    async with websockets.connect(uri, extra_headers={"Origin": "https://spc-studio.onrender.com"}) as ws:
        print("Connected!")
        await asyncio.sleep(10)
        print("Sent ping at 10s")
        await ws.send(json.dumps({"ping": True}))
        try:
            res = await asyncio.wait_for(ws.recv(), timeout=5)
            print("Received:", res)
        except Exception as e:
            print("Error type:", type(e).__name__)
            print("Error details:", str(e))
            traceback.print_exc()

asyncio.run(test())
