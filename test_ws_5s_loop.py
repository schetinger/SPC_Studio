import asyncio
import websockets
import json

async def test():
    uri = "wss://spc-studio.onrender.com/ws/esp/"
    async with websockets.connect(uri, extra_headers={"Origin": "https://spc-studio.onrender.com"}) as ws:
        print("Connected!")
        for i in range(8):
            await asyncio.sleep(5)
            print(f"Sending ping at {i*5 + 5}s")
            await ws.send(json.dumps({"ping": True}))
            try:
                res = await asyncio.wait_for(ws.recv(), timeout=2)
                print(f"Received at {i*5 + 5}s:", res)
            except Exception as e:
                print("Error:", e)
                break
        print("Done!")

asyncio.run(test())
