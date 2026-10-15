import asyncio, json, websockets
EVENT_ID = 1  # Change this to an existing event ID.
URL = f"ws://127.0.0.1:8000/api/v1/events/{EVENT_ID}/availability/ws"
async def main():
    print("Connecting to:", URL)
    async with websockets.connect(URL) as ws:
        print("Connected. Initial availability:", json.loads(await ws.recv()))
        print("Keep this running, then create/cancel one booking in Swagger.")
        while True: print("Update:", json.loads(await ws.recv()))
if __name__ == "__main__": asyncio.run(main())
