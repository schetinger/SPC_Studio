import asyncio
import websockets
import json
import time

async def test():
    uri = "wss://spc-studio.onrender.com/ws/esp/"
    async with websockets.connect(uri, extra_headers={"Origin": "https://spc-studio.onrender.com"}) as ws:
        print("Connected!")
        await asyncio.sleep(15)
        print("Sending ping at 15s")
        await ws.send(json.dumps({"ping": True}))
        try:
            res = await asyncio.wait_for(ws.recv(), timeout=5)
            print("Received at", time.time(), ":", res)
        except Exception as e:
            print("Error receiving ping reply:", e)
        
        print("Waiting until 35s to see if connection drops...")
        try:
            res = await asyncio.wait_for(ws.recv(), timeout=20)
            print("Received unexpected:", res)
        except asyncio.TimeoutError:
            print("Still alive at 35s!")
        except Exception as e:
            print("Disconnected!", e)

asyncio.run(test())
