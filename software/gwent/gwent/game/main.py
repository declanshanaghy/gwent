import asyncio
import logging
import signal

import aioredis

import gwent.log
import gwent.game.cards
import gwent.game.controller
import gwent.game.mfd
import gwent.game.sfx


class Gwent(object):
    _redis = None

    def __init__(self):
        self._log = logging.getLogger(f'{self.__class__.__module__}.{self.__class__.__name__}')

    async def close_redis(self):
        self._redis.close()
        self._log.info('closing redis')
        await self._redis.wait_closed()

    async def shutdown(self, signal, loop):
        """Cleanup tasks tied to the service's shutdown."""
        logging.info(f'Received exit signal {signal.name}...')
        logging.info('Nacking outstanding tasks')
        tasks = [t for t in asyncio.all_tasks() if t is not
                 asyncio.current_task()]

        logging.info(f'Cancelling {len(tasks)} outstanding tasks')
        [task.cancel() for task in tasks]

        tasks.append(self.close_redis())
        await asyncio.gather(*tasks, return_exceptions=True)

        loop.stop()

    def setup_signal_handlers(self, loop):
        # Setup signal handlers for graceful exit
        for s in (signal.SIGABRT, signal.SIGHUP, signal.SIGINT,
                  signal.SIGQUIT, signal.SIGTERM):
            loop.add_signal_handler(
                s, lambda s=s: loop.create_task(self.shutdown(s, loop)))

    async def main(self):
        loop = asyncio.get_running_loop()

        self.setup_signal_handlers(loop)

        self._redis = await aioredis.create_redis_pool('redis://localhost')
        reader = gwent.game.cards.Reader(loop, self._redis)
        controller = gwent.game.controller.Controller(loop, self._redis)
        sfx = gwent.game.sfx.SFX(loop, self._redis)
        mfd = gwent.game.mfd.MFD(loop, self._redis)

        await asyncio.gather(
            reader.run(),
            controller.run(),
            sfx.run(),
            mfd.run(),
        )


if __name__ == '__main__':
    gwent.log.setup(level='debug')
    try:
        asyncio.run(Gwent().main())
    except asyncio.CancelledError as ex:
        logging.info(str(ex))
