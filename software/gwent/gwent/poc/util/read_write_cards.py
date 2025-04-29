import json
import signal
import sys
import time
import threading

from gwent.utils.logging import get_logger, configure_logging, DEBUG

import gwent.game
import gwent.messaging.base
import gwent.cards.all
import gwent.messaging.card
import gwent.cards.util
import gwent.cards.scoiatael
import gwent.hal.rfid
import gwent.hal.sfx


class CardWriterUtil(gwent.game.BaseComponent):
    def __init__(self):
        super().__init__()
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
    def __init__(self):
        super().__init__()
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
        
        print("\nPlease place a card on the reader...")
        self._log.info("Please place a card on the reader...")
        
        card = None
        while card is None and not self._stop_event.is_set():
            card = reader.read_card()
            if card is None:
                # Small delay to prevent CPU hogging
                time.sleep(0.1)
        
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
                
            # Print card details
            print(f"\nCard Read:")
            print(f"  Name:    {card.name if hasattr(card, 'name') else 'Unknown'}")
            print(f"  Faction: {card.faction if hasattr(card, 'faction') else 'Unknown'}")
            print(f"  RFID:    {card.rfid if hasattr(card, 'rfid') else 'Unknown'}")
            if hasattr(card, 'instance'):
                print("\nCard Attributes:")
                if 'strength' in card._instance:
                    print(f"  Strength: {card._instance['strength']}")
                if 'ranges' in card._instance:
                    print(f"  Ranges:   {', '.join(card._instance['ranges'])}")
                if 'specialty' in card._instance:
                    print(f"  Specialty: {card._instance['specialty']}")
                if 'abilities' in card._instance:
                    print(f"  Abilities: {', '.join(card._instance['abilities'])}")

        return card

    def run(self):
        """Run the card reader utility"""
        self.setup_signal_handlers()
        
        return self.read_card()


# entrypoint to write a card
def write_card(card: gwent.messaging.card.Message, file_path: str = None):
    # Create and run the card writer utility
    writer = CardWriterUtil()
    rfid = writer.run(card)
    
    # If successful and we have a file path, update the JSON file with the RFID
    if rfid is not None and file_path is not None:
        try:
            # Read the current JSON file
            with open(file_path, 'r') as f:
                card_data = json.load(f)
            
            # Update the RFID
            card_data['rfid'] = rfid
            
            # Write back to the file
            with open(file_path, 'w') as f:
                json.dump(card_data, f, indent=4)
                
            print(f"\nUpdated JSON file with RFID: {rfid}")
            get_logger('read-write-cards').info(f"Updated JSON file with RFID: {rfid}")
        except Exception as e:
            print(f"\nError updating JSON file: {e}")
            get_logger('read-write-cards').error(f"Error updating JSON file: {e}")
    
    return rfid


# entrypoint to read a card
def read_card():
    # Create and run the card reader utility
    reader = CardReaderUtil()
    return reader.run()


if __name__ == '__main__':
    # Set up logging
    configure_logging(level=DEBUG)

    log = get_logger(f'read-write-cards')
    log.info(f'Received args {sys.argv}...')

    if len(sys.argv) > 1 and sys.argv[1] == 'write':
        card = None
        file_path = None
        if len(sys.argv) == 3:
            file_path = sys.argv[2]  # Get the file path
            card = gwent.cards.util.read_card(file_path)
        else:
            card = gwent.cards.util.random_card()
        write_card(card, file_path)
    else:
        read_card()
