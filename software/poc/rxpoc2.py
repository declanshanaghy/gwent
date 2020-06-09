import rx
from rx import of, operators as op

def length_more_than_5():
    return rx.pipe(
        op.map(lambda s: len(s)),
        op.filter(lambda o: o >= 5))

of("Alpha", "Beta", "Gamma", "Delta", "Epsilon").pipe(
    length_more_than_5()
).subscribe(lambda value: print("Received {0}".format(value)))

def lowercase():
    def _lowercase(source):
        def subscribe(observer, scheduler=None):
            def on_next(value):
                observer.on_next(value.lower())
            return source.subscribe(
                on_next,
                observer.on_error,
                observer.on_completed,
                scheduler
            )
        return rx.create(subscribe)
    return _lowercase

of("Alpha", "Beta", "Gamma", "Delta", "Epsilon").pipe(
    lowercase()
).subscribe(lambda v: print(v))
