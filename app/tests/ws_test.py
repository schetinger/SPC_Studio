import asyncio
import websockets
import json

async def test():
    try:
        async with websockets.connect("ws://127.0.0.1:8000/ws/monitor/") as ws:
            print("Connected to MonitorConsumer")
            msg = await ws.recv()
            print("Received on connect:", msg[:100], "...")
            
            print("Sending ligar_alerta")
            await ws.send(json.dumps({"comando": "ligar_alerta"}))
            
            msg = await ws.recv()
            print("Received after command:", msg[:100], "...")
            
    except Exception as e:
        print("Error:", e)

asyncio.get_event_loop().run_until_complete(test())
