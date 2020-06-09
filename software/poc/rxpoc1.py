from typing import Optional
from rx.core.typing import Observer, Scheduler, Disposable
from rx import create

def push_five_strings(observer: Observer, _: Optional[Scheduler]):
    observer.on_next("Alpha")
    observer.on_next("Beta")
    observer.on_next("Gamma")
    observer.on_next("Delta")
    observer.on_next("Epsilon")
    observer.on_completed()

source = create(push_five_strings)

source.subscribe(
    on_next = lambda i: print("Received {0}".format(i)),
    on_error = lambda e: print("Error Occurred: {0}".format(e)),
    on_completed = lambda: print("Done!"),
)
