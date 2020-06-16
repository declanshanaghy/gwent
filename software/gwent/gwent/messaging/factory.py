import json
import logging

import gwent.messaging.base
import gwent.messaging.card
import gwent.messaging.ctrl
import gwent.messaging.choice
import gwent.messaging.mfd
import gwent.messaging.sfx


_log = logging.getLogger('factory')


class UnexpectedKind(Exception):
    pass


class UnhandledFactoryKind(Exception):
    pass


_constructors = {
    gwent.messaging.card.KIND: gwent.messaging.card.Message,
    gwent.messaging.ctrl.KIND: gwent.messaging.ctrl.Message,
    gwent.messaging.choice.KIND: gwent.messaging.choice.Message,
    gwent.messaging.mfd.KIND: gwent.messaging.mfd.Message,
    gwent.messaging.sfx.KIND: gwent.messaging.sfx.Message,
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
