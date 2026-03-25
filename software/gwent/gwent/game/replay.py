import json
import time

from gwent.utils.logging import get_logger

log = get_logger("gwent.game.replay")

MAX_DELAY = 20.0


def replay(pubsub, filepath: str):
    """Replay a JSONL trace file into the MQTT bus using real-time delays.

    Timing between messages uses the original recorded timestamps,
    capped at MAX_DELAY seconds. The tracer is responsible for only
    recording input topics, so all messages in the file are replayed.

    Args:
        pubsub: The MQTT client to publish messages on.
        filepath: Path to a .jsonl trace file recorded by tracer.py.
    """
    import gwent.game.tracer as tracer
    tracer.disable()

    log.info(f"Replaying trace from {filepath}")
    count = 0
    prev_ts = None

    with open(filepath, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            entry = json.loads(line)
            ts = entry["ts"]
            topic = entry["topic"]
            payload = entry["payload"]

            # Real-time delay between messages, capped
            if prev_ts is not None:
                delay = min(ts - prev_ts, MAX_DELAY)
                if delay > 0:
                    time.sleep(delay)
            prev_ts = ts

            log.info(f"replay: {topic}")
            pubsub.publish(topic, payload, qos=0)
            count += 1
            # Give components time to process before next input
            time.sleep(0.5)

    log.info(f"Replay complete: {count} messages from {filepath}")
    tracer.enable()
