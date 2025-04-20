import asyncio

import asyncio_mqtt

import gwent.game
import gwent.messaging.card_play
import gwent.messaging.factory
import gwent.messaging.sfx
import gwent.hal.matrix


class Player(gwent.game.PubSubComponent):

    def __init__(self, player:str, loop: asyncio.AbstractEventLoop,
                 pubsub: asyncio_mqtt.Client):
        super().__init__(loop, pubsub)
        self._player = player
        self._channel = gwent.game.make_channel(
            gwent.game.CH_CARDS_PLAY, self._player)

    async def init(self):
        self._matrix = await gwent.hal.matrix.instance(self._loop)
        await self.subscribe(self._channel, gwent.messaging.card_play.KIND,
                             self.process_card_play)

    async def shutdown(self):
        await self.unsubscribe(gwent.messaging.sfx.KIND)

    async def process_card_play(self, cp: gwent.messaging.card_play.Message):
        self._log.info({
            'action': f'received {cp.kind}',
            'subkind': cp.subkind,
            'faction': cp.card.faction,
            'name': cp.card.name,
            'strength': cp.card.strength,
        })

        if cp.subkind == gwent.messaging.card_play.ADD_TO_DECK:
            await self._matrix.display_score(cp.card.strength)
        else:
            self._log.error(f'Unhandled subkind: {cp.subkind}')

