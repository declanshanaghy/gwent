import json
import logging
from typing import List

import gwent.messaging.base
import gwent.messaging.cards.card
import gwent.messaging.mfd.choice
import gwent.messaging.mfd.mfd
import gwent.messaging.sfx.sfx


_log = logging.getLogger('factory')


class UnexpectedKind(Exception):
    pass


class UnhandledFactoryKind(Exception):
    pass


_constructors = {
    gwent.messaging.cards.card.KIND: gwent.messaging.cards.card.Message,
    gwent.messaging.mfd.choice.KIND: gwent.messaging.mfd.choice.Message,
    gwent.messaging.mfd.mfd.KIND: gwent.messaging.mfd.mfd.Message,
    gwent.messaging.sfx.sfx.KIND: gwent.messaging.sfx.sfx.Message,
}

def unmarshall(msg: str, expect_kind:str=None) -> gwent.messaging.base.Message:
    instance = json.loads(msg)

    kind = instance[gwent.messaging.base.KIND]
    if expect_kind is not None and not kind == expect_kind:
        error = f'Expected {expect_kind} but received {kind}, {instance}'
        _log.error({
            'error': error,
            'instance': instance,
        })
        raise UnexpectedKind(error)

    cls = _constructors.get(kind)
    if cls is None:
        error = f'Unhandled kind: {kind}, {instance}'
        _log.error({
            'error': error,
            'instance': instance,
        })
        raise UnhandledFactoryKind(error)

    message = cls(instance)
    return message
