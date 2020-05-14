#!/usr/bin/env python3

# WS server that sends messages at random intervals

import asyncio
import logging
import http
import json
import signal
import datetime

import websockets

import log
import cards.io


class Server(object):
    _log = logging.getLogger(__name__)
    _clients = dict()
    _reading_card_task = None
    _card_reader = cards.io.Reader()

    async def _producer(self, websocket: websockets.WebSocketServerProtocol,
                        client_q: asyncio.Queue):
        self._log.info({
            'action': 'new producer',
            'remote_address': ("%s:%s" % websocket.remote_address),
        })
        while True:
            message = await client_q.get()

            if message is not None:
                self._log.debug({
                    'action': 'send message',
                    'message': message,
                })
                await websocket.send(json.dumps(message))

    async def _consumer(self, websocket: websockets.WebSocketServerProtocol,
                        client_q: asyncio.Queue):
        self._log.info({
            'action': 'new connection',
            'remote_address': ("%s:%s" % websocket.remote_address),
        })
        # Send current status
        await self._send_status_to_client(client_q)

        try:
            async for message in websocket:
                try:
                    decoded = json.loads(message)
                    result = await self._consume(decoded, client_q)
                    await self._queue(client_q, result)
                except json.decoder.JSONDecodeError:
                    await self._send_status_to_client(
                        client_q, code=http.HTTPStatus.BAD_REQUEST)
        except websockets.exceptions.ConnectionClosedError as ex:
            self._log.warning({
                'action': 'client disconnected',
                'ex': ex
            })

    async def _queue(self, client_q, message):
        message['datetime'] = datetime.datetime.now().isoformat()
        await client_q.put(message)

    async def _consume(self, message, client_q):
        self._log.info({
            'action': 'received message',
            'message': message,
        })
        action = message['action']
        payload = message['payload']

        if action == 'set_state':
            if 'reading_card' in payload:
                if payload['reading_card']:
                    self._start_card_reader()
                else:
                    self._stop_card_reader()
            # Since the state changed...
            # ...send out an update to other clients
            await self._send_status_to_others(client_q)

        # ...send out an update to this client with code = OK
        return self._new_status(code=http.HTTPStatus.OK)

    async def _serve(self, websocket: websockets.WebSocketServerProtocol,
                     path: str):
        self._log.info({
            'action': 'serving',
            'remote_address': ("%s:%s" % websocket.remote_address),
            'path': path,
        })

        # Create an outgoing queue for dedicated communication to this client
        client_q = asyncio.Queue()

        self._clients[websocket] = client_q

        try:
            consumer = asyncio.ensure_future(
                self._consumer(websocket, client_q))
            producer = asyncio.ensure_future(
                self._producer(websocket, client_q))
            done, pending = await asyncio.wait(
                [
                    consumer,
                    producer,
                ],
                return_when=asyncio.FIRST_COMPLETED,
            )
            for task in pending:
                task.cancel()
        except asyncio.CancelledError as ex:
            self._log.warning({
                'action': 'task canceled',
                'ex': ex
            })
        finally:
            del self._clients[websocket]

    async def _send_status_to_all(self, code: int = http.HTTPStatus.CONTINUE):
        await self._send_all(self._new_status(code=code))

    async def _send_status_to_others(self, client_q,
                                     code: int = http.HTTPStatus.CONTINUE):
        await self._send_all_except(
            self._new_status(code=code), client_q=client_q)

    async def _send_status_to_client(self, client_q,
                                     code: int = http.HTTPStatus.CONTINUE):
        await self._queue(client_q, self._new_status(code))

    def _new_status(self, code: int = http.HTTPStatus.CONTINUE):
        return self._new_message(
            'status',
            payload={
                'code': code,
                'reading_card': self._card_reader_running(),
            }
        )

    def _new_message(self, action, payload=None):
        message = {'action': action}
        if payload is not None:
            message['payload'] = payload
        return message

    async def _send_all(self, message):
        await self._send_all_except(message)

    async def _send_all_except(self, message, client_q=None):
        tasks = []
        for this_q in self._clients.values():
            if client_q != this_q:
                tasks.append(self._queue(this_q, message))
        n_tasks = len(tasks)
        if n_tasks > 0:
            self._log.info({
                'action': f'sending message to {n_tasks} clients',
                'message': message,
            })
            await asyncio.wait(tasks)

    def _card_reader_running(self):
        return (self._reading_card_task is not None and
                not self._reading_card_task.done())

    def _card_reader_done(self, future):
        self._log.info({
            'action': '_card_reader_done',
            'future': future,
        })
        loop = asyncio.get_event_loop()
        loop.create_task(self._send_status_to_all())

    def _start_card_reader(self):
        if not self._card_reader_running():
            self._log.info({
                'action': '_start_card_reader',
            })
            loop = asyncio.get_event_loop()
            self._reading_card_task = loop.create_task(self._read_card_loop())
            self._reading_card_task.add_done_callback(self._card_reader_done)
        else:
            self._log.warning('cannot start card reader, already reading')

    def _stop_card_reader(self):
        if self._card_reader_running():
            self._log.info({
                'action': '_stop_card_reader',
            })
            self._reading_card_task.cancel()
        else:
            self._log.warning('cannot stop card reader, not reading')

    async def _read_card_loop(self):
        loop = asyncio.get_running_loop()
        self._log.info({
            'action': '_read_card_loop',
            'status': 'start',
        })

        try:
            while True:
                id, text = await loop.run_in_executor(
                    None, self._card_reader.read)
                if id is None:
                    continue

                details = {}
                try:
                    details = json.loads(text)
                    self._log.warning({
                        'action': 'Read existing card',
                        'id': id,
                        'details': details,
                    })
                except json.decoder.JSONDecodeError:
                    self._log.warning({
                        'action': 'read a blank card. No details',
                        'id': id,
                    })
                    details = {'text': text}

                message = self._new_message(
                    'card_read',
                    payload={
                        'id': id,
                        'details': details,
                    })

                n_clients = len(self._clients.keys())
                if n_clients > 0:
                    await self._send_all(message)
                await asyncio.sleep(1.0)
        finally:
            self._log.info({
                'action': '_read_card_loop',
                'status': 'finished',
            })

    async def shutdown(self, signal, loop):
        """Cleanup tasks tied to the service's shutdown."""
        logging.info(f'Received exit signal {signal.name}...')
        logging.info('Nacking outstanding tasks')
        tasks = [t for t in asyncio.all_tasks() if t is not
                 asyncio.current_task()]

        logging.info(f'Cancelling {len(tasks)} outstanding tasks')
        [task.cancel() for task in tasks]
        await asyncio.gather(*tasks, return_exceptions=True)

        loop.stop()

    def run(self):
        self._log.info("run")

        loop = asyncio.get_event_loop()

        # Setup signal handlers for graceful exit
        for s in (signal.SIGABRT, signal.SIGHUP, signal.SIGINT,
                  signal.SIGQUIT, signal.SIGTERM):
            loop.add_signal_handler(
                s, lambda s=s: asyncio.create_task(self.shutdown(s, loop)))

        try:
            # self._start_card_reader()

            address = {
                'host': '0.0.0.0',
                'port': 8888
            }
            self._log.info({
                'action': 'listen',
                'address': address,
            })
            server = websockets.serve(self._serve, **address)
            loop.run_until_complete(server)
            loop.run_forever()
        finally:
            loop.close()
            self._log.info("exiting")


def run():
    # log.setup(level='debug')
    log.setup()
    server = Server()
    server.run()


if __name__ == '__main__':
    run()
