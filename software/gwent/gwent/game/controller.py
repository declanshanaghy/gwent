import aioredis

import gwent.messaging.base
import gwent.messaging.cards.card
import gwent.messaging.factory
import gwent.messaging.mfd.mfd
import gwent.messaging.mfd.choice
import gwent.messaging.sfx
import gwent.game
import gwent.hal.tts


class Controller(gwent.game.Component):
    active_state = None
    registration = None

    def __init__(self, loop, redis: aioredis.Redis):
        super().__init__(loop, redis)
        self.registration = RegisterPlayers(self._loop, self._redis)
        self.active_state = self.registration

    async def run(self):
        await self.subscribe(self.process,
                             gwent.game.CH_CARDS_RAW_READ,
                             gwent.game.CH_MFD_CHOICE,
                             expect=[gwent.messaging.cards.card.KIND,
                                     gwent.messaging.mfd.choice.KIND])

    async def process(self, message: gwent.messaging.cards.card.Message):
        await self.active_state.process(message)


class CameControllerState(gwent.game.Component):
    pass


class RegisterPlayers(CameControllerState):
    async def process(self, message: gwent.messaging.base.Message):
        if message.kind == gwent.messaging.cards.card.KIND:
            await self.process_card(message)
        elif message.kind == gwent.messaging.mfd.choice.KIND:
            await self.process_choice(message)

    async def process_card(self, card: gwent.messaging.cards.card.Message):
        self._log.info({
            'action': 'received card',
            'kind': card.kind,
            'rfid': card.rfid,
        })

        choices = [
            gwent.messaging.mfd.choice.Message.from_properties('1', 'hello world'),
            gwent.messaging.mfd.choice.Message.from_properties('2', 'goodbye world')
        ]
        mfd = gwent.messaging.mfd.mfd.Message.from_properties(choices)
        await self.publish(gwent.game.CH_MFD_PRESENT, mfd)

    async def process_choice(self, choice: gwent.messaging.mfd.choice.KIND):
        self._log.info({
            'action': 'received choice',
            'kind': choice.kind,
            'id': choice.id,
        })
