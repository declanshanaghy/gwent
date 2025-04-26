import logging
import signal
import sys
import time
import threading

import gwent.log
import gwent.game
import gwent.messaging.base
import gwent.cards.all
import gwent.messaging.card
import gwent.cards.util
import gwent.cards.scoiatael
import gwent.hal.rfid
import gwent.hal.sfx


class CardWriterUtil(gwent.game.BaseComponent):
    def __init__(self, log_verbose: bool = False):
        super().__init__(log_verbose=log_verbose)
        self._stop_event = threading.Event()
        
    def setup_signal_handlers(self):
        """Setup signal handlers for graceful exit"""
        def signal_handler(sig, frame):
            self._log.info(f'Received exit signal {signal.Signals(sig).name}...')
            self._stop_event.set()
            
        for s in (signal.SIGABRT, signal.SIGHUP, signal.SIGINT,
                  signal.SIGQUIT, signal.SIGTERM):
            signal.signal(s, signal_handler)

    def write_card(self, card: gwent.messaging.card.Message):
        """Write a card using the RFID writer"""
        self._log.info({
            'action': 'Hold a tag near the writer to receive the data',
            'name': card.name,
            'faction': card.faction,
        })

        writer = gwent.hal.rfid.instance()

        id = None
        while id is None and not self._stop_event.is_set():
            id = writer.write_card(card)
            if id is None:
                # Small delay to prevent CPU hogging
                time.sleep(0.1)

        if id is not None:
            self._log.info({
                'action': 'card written successfully',
                'id': id,
            })
            
        return id

    def run(self, card: gwent.messaging.card.Message):
        """Run the card writer utility"""
        self.setup_signal_handlers()

        self._log.info({
            'action': 'run',
            'full_name': card.full_name,
            'faction': card.faction,
        })
        
        return self.write_card(card)


class CardReaderUtil(gwent.game.BaseComponent):
    def __init__(self, log_verbose: bool = False):
        super().__init__(log_verbose=log_verbose)
        self._stop_event = threading.Event()
        
    def setup_signal_handlers(self):
        """Setup signal handlers for graceful exit"""
        def signal_handler(sig, frame):
            self._log.info(f'Received exit signal {signal.Signals(sig).name}...')
            self._stop_event.set()
            
        for s in (signal.SIGABRT, signal.SIGHUP, signal.SIGINT,
                  signal.SIGQUIT, signal.SIGTERM):
            signal.signal(s, signal_handler)

    def read_card(self) -> gwent.messaging.card.Message:
        """Read a card using the RFID reader"""
        reader = gwent.hal.rfid.instance()

        card = reader.read_card()
        if card is not None:
            self._log.info({
                'action': 'got card',
                'rfid': card.rfid,
                'name': card.name,
                'faction': card.faction,
            })

            # Play sound effect for the card
            try:
                sfx = gwent.hal.sfx.SFXPlayer()
                sfx.announce_card(card)
            except Exception as e:
                self._log.error(f"Error playing sound: {e}")

        return card

    def run(self):
        """Run the card reader utility"""
        self.setup_signal_handlers()
        
        return self.read_card()


# entrypoint to write a card
def write_card(card: gwent.messaging.card.Message):
    # Set up logging
    gwent.log.setup(level='debug')

    # Create and run the card writer utility
    writer = CardWriterUtil()
    return writer.run(card)


# entrypoint to read a card
def read_card():
    # Set up logging
    gwent.log.setup(level='debug')

    # Create and run the card reader utility
    reader = CardReaderUtil()
    return reader.run()


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'write':
        card = None
        if len(sys.argv) == 3:
            card = sys.argv[2]  # Fixed index from 3 to 2
            card = gwent.cards.util.read_card(card)
        else:
            card = gwent.cards.util.random_card()
        write_card(card)
    else:
        read_card()
