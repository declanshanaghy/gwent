import asyncio
import logging
import signal

import aioredis

import pygame.mixer
import pygame

import gwent.log
import gwent.game.cards
import gwent.hal.tts


class Gwent(object):
    _log = logging.getLogger(__name__)
    _redis = None

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
                s, lambda s=s: asyncio.create_task(self.shutdown(s, loop)))

    def setup_pygame(self):
        pygame.mixer.init(frequency=44100, size=-16, channels=2)
        pygame.init()

    async def main(self):
        loop = asyncio.get_running_loop()

        self.setup_pygame()
        self.setup_signal_handlers(loop)

        self._redis = await aioredis.create_redis_pool('redis://localhost')
        reader = gwent.game.cards.Reader(loop, self._redis)
        announcer = gwent.game.cards.Announcer(loop, self._redis)

        await  asyncio.gather(
            reader.run(),
            announcer.run(),
        )


if __name__ == '__main__':
    gwent.log.setup()
    try:
        asyncio.run(Gwent().main())
    except asyncio.CancelledError as ex:
        logging.info(str(ex))
