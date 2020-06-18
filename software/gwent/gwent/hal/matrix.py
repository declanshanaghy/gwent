import asyncio

import aioconsole

import gwent.game
import gwent.hal


async def instance(loop:asyncio.AbstractEventLoop):
    if await gwent.hal.real_mode():
        return _RealMatrix(loop, log_verbose=False)
    else:
        return _FakeMatrix(loop)


class _FakeMatrix(gwent.game.GameComponent):
    async def display_score(self, score: int):
        self._log.info({
            'action': 'display score',
            'score': score
        })


class _RealMatrix(gwent.game.GameComponent):
    async def display_score(self, score: int):
        await aioconsole.aprint(f'New score: {score}')
