import asyncio
import websockets
import json

async def test():
    uri = "wss://spc-studio.onrender.com/ws/esp/"
    async with websockets.connect(uri, extra_headers={"Origin": "https://spc-studio.onrender.com"}) as ws:
        print("Connected!")
        for i in range(5):
            await asyncio.sleep(1)
            print(f"Sending ping {i+1} at {i+1}s")
            await ws.send(json.dumps({"ping": True}))
            try:
                res = await asyncio.wait_for(ws.recv(), timeout=2)
                print(f"Received {i+1}:", res)
            except Exception as e:
                print("Error type:", type(e).__name__)
                break
        print("Done!")

asyncio.run(test())
