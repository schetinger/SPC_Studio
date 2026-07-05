import asyncio
import websockets
import json

async def test():
    uri = "ws://localhost:8001/ws/esp/"
    async with websockets.connect(uri) as ws:
        print("Connected locally!")
        for i in range(8):
            await asyncio.sleep(5)
            print(f"Sending ping at {i*5 + 5}s")
            await ws.send(json.dumps({"ping": True}))
            try:
                res = await asyncio.wait_for(ws.recv(), timeout=2)
                print(f"Received at {i*5 + 5}s:", res)
            except Exception as e:
                print("Error type:", type(e).__name__)
                break
        print("Done locally!")

asyncio.run(test())
