#!/usr/bin/env python3

# WS server that sends messages at random intervals

import asyncio
import logging
import http
import json

import websockets

import log
import rfid.io

class Server(object):
    _log = logging.getLogger(__name__)
    _clients = dict()
    _rfid = rfid.io.RFIDio()

    async def _producer(self, websocket, q):
        self._log.info({
            'action': '_producer',
            'remote_address': ("%s:%s" % websocket.remote_address),
        })
        while True:
            message = await q.get()

            if message is not None:
                self._log.info({
                    'action': 'send message',
                    'message': message,
                })
                await websocket.send(json.dumps(message))

    async def _consumer(self, websocket, q):
        self._log.info({
            'action': '_consumer',
            'remote_address': ("%s:%s" % websocket.remote_address),
        })
        # Send continue status
        await self._queue(q, {
            'kind': 'status',
            'status': http.HTTPStatus.CONTINUE.value
        })
        async for message in websocket:
            result = await self._consume(message)
            await self._queue(q, result)

    async def _queue(self, q, message):
        self._log.info({
            'action': '_queue',
            'message': message,
        })
        await q.put(message)

    async def _consume(self, message):
        self._log.info({
            'action': '_consume',
            'message': message,
        })
        return {
            'kind': 'status',
            'status': http.HTTPStatus.OK.value
        }

    async def _rfid_read(self, q):
        loop = asyncio.get_running_loop()
        self._log.info({
            'action': '_rfid_read',
        })
        while True:
            id, text = await loop.run_in_executor(None, self._rfid.read)
            message = {
                'id': id,
                'text': text,
            }

            self._log.info({
                'action': '_rfid_read',
                'id': id,
                'text': text,
            })
            await self._queue(q, message)

    async def _serve(self, websocket, path):
        loop = asyncio.get_event_loop()

        self._log.info({
            'action': '_serve',
            'remote_address': ("%s:%s" % websocket.remote_address),
            'path': path,
        })

        # Create an outgoing queue for dedicated communication to this client
        q = asyncio.Queue()

        self._clients[websocket] = q

        try:
            rfid_read = await loop.run_in_executor(None, self._rfid_read, q)
            consumer = asyncio.ensure_future(self._consumer(websocket, q))
            producer = asyncio.ensure_future(self._producer(websocket, q))
            done, pending = await asyncio.wait(
                [
                    rfid_read,
                    consumer,
                    producer,
                ],
                return_when=asyncio.FIRST_COMPLETED,
            )
            for task in pending:
                task.cancel()
        finally:
            del self._clients[websocket]

    def run(self):
        self._log.info("run")

        server = websockets.serve(self._serve, "0.0.0.0", 8444)
        asyncio.get_event_loop().run_until_complete(server)
        asyncio.get_event_loop().run_forever()
        self._log.info("exited")


def run():
    # log.setup(level='debug')
    log.setup()
    server = Server()
    server.run()


if __name__ == '__main__':
    run()
