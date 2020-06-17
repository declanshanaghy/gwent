import asyncio
import logging
import signal

import asyncio_mqtt

import gwent.log
import gwent.game.cards
import gwent.game.controller
import gwent.game.mfd
import gwent.game.sfx
import gwent.hal


class Gwent(object):
    pubsub = None

    def __init__(self):
        self._log = logging.getLogger(f'{self.__class__.__module__}.{self.__class__.__name__}')

    async def close_redis(self):
        self._log.info('closing pubsub')
        await self.pubsub.disconnect()

    async def shutdown_components(self):
        if self.components is not None:
            logging.info('Shutting down components')
            await asyncio.gather(*[c.shutdown() for c in self.components])

    async def shutdown(self):
        await self.close_redis()

    async def sighandler(self, signal, loop):
        """Cleanup tasks tied to the service's shutdown."""
        logging.info(f'Received exit signal {signal.name}...')

        await self.shutdown_components()

        tasks = [t for t in asyncio.all_tasks() if t is not
                 asyncio.current_task()]
        logging.info(f'Canceling {len(tasks)} outstanding tasks')
        [task.cancel() for task in tasks]
        tasks.append(self.shutdown())
        await asyncio.gather(*tasks, return_exceptions=True)

        loop.stop()

    def setup_signal_handlers(self, loop):
        # Setup signal handlers for graceful exit
        for s in (signal.SIGABRT, signal.SIGHUP, signal.SIGINT,
                  signal.SIGQUIT, signal.SIGTERM):
            loop.add_signal_handler(
                s, lambda s=s: loop.create_task(self.sighandler(s, loop)))

    async def main(self):
        loop = asyncio.get_running_loop()

        self.setup_signal_handlers(loop)

        self.pubsub = asyncio_mqtt.Client('localhost')
        await self.pubsub.connect()

        self.components = [
            gwent.game.controller.Controller(loop, self.pubsub),
            gwent.game.cards.Reader(loop, self.pubsub),
            gwent.game.mfd.MFD(loop, self.pubsub),
            gwent.game.sfx.SFX(loop, self.pubsub),
        ]

        logging.info('Init components')
        await asyncio.gather(*[c.init() for c in self.components])

        logging.info('Run components')
        await asyncio.gather(*[c.run() for c in self.components])

        await self.shutdown_components()
        await self.shutdown()


def run():
    gwent.log.setup(level='debug')
    try:
        asyncio.run(Gwent().main(), debug=False)
    except asyncio.CancelledError as ex:
        logging.info(str(ex))


if __name__ == '__main__':
    run()
