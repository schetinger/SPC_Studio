import asyncio
import websockets
import json

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
            print("Error receiving, but let's check if alive by sending again!")
            await ws.send(json.dumps({"ping": True}))
            try:
                res = await asyncio.wait_for(ws.recv(), timeout=5)
                print("Received after second attempt:", res)
            except Exception as e2:
                print("Error again:", e2)

asyncio.run(test())
