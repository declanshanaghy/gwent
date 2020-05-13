#!/usr/bin/env python3

# WS server that sends messages at random intervals

import asyncio
import logging
import queue
import http
import json

import websockets

import log


class Server(object):
    log = logging.getLogger(__name__)

    async def producer_handler(self, websocket, path, q):
        self.log.info({
            'action': 'producer_handler',
            'websocket': websocket,
            'path': path,
        })
        while True:
            try:
                message = q.get(block=True, timeout=10)
            except queue.Empty:
                self.log.debug({
                    'action': 'no message',
                })
                continue

            self.log.info({
                'action': 'send message',
                'message': message,
            })
            await websocket.send(json.dumps(message))

    async def consumer_handler(self, websocket, path, q):
        self.log.info({
            'action': 'consumer_handler',
            'websocket': websocket,
            'path': path,
        })
        # Send continue status
        self.queue(q, {
            'kind': 'status',
            'status': http.HTTPStatus.CONTINUE.value
        })
        async for message in websocket:
            result = await self.consume(message)
            self.queue(q, result)

    def queue(self, q, message):
        self.log.info({
            'action': 'queue',
            'message': message,
        })
        q.put(message)

    async def consume(self, message):
        self.log.info({
            'action': 'consume',
            'message': message,
        })
        return {
            'kind': 'status',
            'status': http.HTTPStatus.OK.value
        }

    def run(self):
        self.log.info("run")

        async def handler(websocket, path):
            self.log.info({
                'action': 'handler',
                'websocket': websocket,
                'path': path,
            })

            # Create an outgoing queue for this socket
            q = queue.Queue()

            consumer_task = asyncio.ensure_future(
                self.consumer_handler(websocket, path, q))
            # producer_task = asyncio.ensure_future(
            #     self.producer_handler(websocket, path, q))
            done, pending = await asyncio.wait(
                [
                    consumer_task,
                    # producer_task
                ],
                return_when=asyncio.FIRST_COMPLETED,
            )
            for task in pending:
                task.cancel()

        start_server = websockets.serve(handler, "0.0.0.0", 8444)
        asyncio.get_event_loop().run_until_complete(start_server)
        asyncio.get_event_loop().run_forever()
        self.log.info("exited")


def run():
    log.setup(level='debug')
    server = Server()
    server.run()


if __name__ == '__main__':
    run()
