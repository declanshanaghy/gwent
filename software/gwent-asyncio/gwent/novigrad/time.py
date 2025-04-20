#!/usr/bin/env python

# WS server that sends messages at random intervals

import asyncio
import datetime
import json
import http
import random
import websockets


async def time(websocket, path):
    while True:
        now = datetime.datetime.utcnow().isoformat() + "Z"
        # await websocket.send(now)
        await websocket.send(json.dumps({
            "kind": 'status',
            'status': http.HTTPStatus.OK,
            'time': now
        }))
        await asyncio.sleep(random.random() * 3)


start_server = websockets.serve(time, "127.0.0.1", 8444)

asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()
