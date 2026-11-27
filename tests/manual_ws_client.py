"""Manual test client for the VoxMate WebSocket voice gateway.

Usage:
    python tests/manual_ws_client.py --token PASTE_ACCESS_TOKEN

Requires: pip install websockets requests
"""
import argparse
import asyncio
import json
import uuid

import requests
import websockets

API_URL = "http://localhost:8000"
WS_URL = "ws://localhost:8000"


async def main(token: str):
    resp = requests.post(f"{API_URL}/sessions", headers={"Authorization": f"Bearer {token}"})
    resp.raise_for_status()
    session_id = resp.json()["session_id"]
    print(f"Session: {session_id}")

    uri = f"{WS_URL}/ws/voice/{session_id}?token={token}"
    async with websockets.connect(uri) as ws:
        print("Connected. Type a message and press Enter (Ctrl+C to quit).")
        while True:
            text = input("you> ")
            await ws.send(json.dumps({"type": "text", "data": text}))
            while True:
                raw = await ws.recv()
                event = json.loads(raw)
                print(f"  <- {event}")
                if event.get("type") == "turn_complete":
                    break


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--token", required=True)
    args = parser.parse_args()
    asyncio.run(main(args.token))
