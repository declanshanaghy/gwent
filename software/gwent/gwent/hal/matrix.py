import threading

import gwent.game
import gwent.hal


def instance():
    if gwent.hal.real_mode():
        return _RealMatrix(log_verbose=False)
    else:
        return _FakeMatrix()


class _FakeMatrix(gwent.game.BaseComponent):
    def display_score(self, score: int):
        self._log.info({
            'action': 'display score',
            'score': score
        })


class _RealMatrix(gwent.game.BaseComponent):
    def display_score(self, score: int):
        print(f'New score: {score}')
