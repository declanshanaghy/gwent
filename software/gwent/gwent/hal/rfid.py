import json
import random
import time
import logging

import gwent.game.cards
import gwent.game.cards.starters
import gwent.log

BLOCK_SIZE = 16
SECTOR_SIZE = 4
SECTOR_WRITABLE = 3

MIN_SECTOR = 1
MAX_SECTOR = 15
ALL_SECTORS = range(MIN_SECTOR, MAX_SECTOR + 1)


class RFIDError(Exception):
    pass

def get_blocks(sector) -> (int, [int]):
    s = sector * 4
    e = s + 3
    blocks = []
    for b in range(s, e):
        blocks.append(b)
    return e, blocks


class Reader(object):
    _log = logging.getLogger(__name__)
    _rfid = None

    def __init__(self):
        try:
            import mfrc522
            self._rfid = mfrc522.SimpleMFRC522()
        except Exception as ex:
            self._log.error({
                'action': 'error setting up MFRC522. Using fake mode',
                'ex': ex,
            })
            random.seed()

    def read(self, block: bool = False, trailer: int = 11,
             blocks: [int] = (8, 9, 10)) -> (int, str):
        if self._rfid is not None:
            id, text = self.read_real(block=block, trailer=trailer, blocks=blocks)
        else:
            id, text = self.read_fake()

        if id:
            return id, text
        else:
            raise RFIDError(f'Error reading sector: '
                            f'trailer={trailer}, blocks={blocks}')

    def read_fake(self) -> (int, str):
        t = float(random.randint(0, 100)) / 100
        self._log.info(f'Will produce a fake tag in {t} seconds')
        time.sleep(t)
        faction = random.choice(gwent.game.cards.starters.ALL_FACTIONS)
        name = random.choice(faction['starters'])
        details = {
            'name': name,
            'faction': faction['name']
        }
        return random.randint(10000000, 999999999), json.dumps(details)

    def read_real(self, block: bool = False, trailer: int = 11,
                  blocks: [int] = (8, 9, 10)) -> (int, str):
        if block:
            # self._log.info("Hold a tag near the reader")
            id, text = self._rfid.read(trailer=trailer, blocks=blocks)
        else:
            id, text = self._rfid.read_no_block(trailer=trailer, blocks=blocks)
        if id:
            text = text.strip()
            return id, text
        else:
            return None, None


class Writer(Reader):
    def write_sector(self, text: str, block: bool = False,
                     trailer: int = 11,
                     blocks: [int] = (8, 9, 10)) -> (int, str):
        if self._rfid is not None:
            if block:
                id, text = self._rfid.write(text, trailer=trailer,
                                            blocks=blocks)
            else:
                id, text = self._rfid.write_no_block(text, trailer=trailer,
                                                     blocks=blocks)
        else:
            id, text = self._write_fake(text, block=block, trailer=trailer,
                                        blocks=blocks)

        if id:
            return id, text
        else:
            raise RFIDError(f'Error writing sector: '
                            f'trailer={trailer}, blocks={blocks}')

    def _write_fake(self, text: str, block: bool = False,
                    trailer: int = 11,
                    blocks: [int] = (8, 9, 10)) -> (int, str):
        if block:
            t = float(random.randint(0, 100)) / 100
        else:
            t = 0

        if self._log.isEnabledFor(logging.DEBUG):
            self._log.debug({
                'action': f'Will fake a write to a tag in {t} seconds',
                'len(text)': len(text),
                'text': text,
                'trailer': trailer,
                'blocks': blocks,
            })

        if t > 0:
            time.sleep(t)

        id = random.randint(10000000, 999999999)
        return id, text

    def write_card(self, card: gwent.game.cards.Card,
                   block: bool = False, write_all: bool = False) -> (int, str):
        sectors = card.sectors
        card_details = str(card)
        if write_all:
            sectors = ALL_SECTORS
        start = time.time()
        if self._log.isEnabledFor(logging.INFO):
            self._log.info({
                'action': 'write_card',
                'card_details': card_details,
                'bytes': card.bytes,
                'blocks': card.blocks,
                'min_sector': card.min_sector,
                'max_sector': card.max_sector,
                'sectors': sectors,
                'block': block,
                'start': start,
            })
        id, text = self.write_str(card_details, block=block, sectors=sectors)
        end = time.time()
        elapsed = end - start
        if self._log.isEnabledFor(logging.INFO):
            self._log.info({
                'action': 'write_card_complete',
                'id': id,
                'text': text,
                'start': start,
                'end': end,
                'elapsed': elapsed,
            })

    def write_str(self, text: str, block: bool = False,
                  sectors: [int] = None) -> (int, str):
        if sectors is None:
            sectors = ALL_SECTORS
        id = None
        total_written = ""

        maxlen = len(text)
        s = 0
        for sector in sectors:
            trailer, blocks = get_blocks(sector)
            e1 = s + (SECTOR_WRITABLE * BLOCK_SIZE)
            e = min(maxlen, e1)
            sector_data = text[s:e]

            # Pad with null if len(data) < 16
            if len(sector_data) < BLOCK_SIZE * len(blocks):
                npad = BLOCK_SIZE * len(blocks) - len(sector_data)
                sector_data += "\0" * npad

            id, sector_written = self.write_sector(
                sector_data, block=block, trailer=trailer, blocks=blocks)

            if self._log.isEnabledFor(logging.DEBUG):
                self._log.debug({
                    'action': 'sector written',
                    'id': id,
                    'sector': sector,
                    'trailer': trailer,
                    'blocks': blocks,
                    'sector_data': sector_data,
                    'len(sector_data)': len(sector_data),
                    'sector_written': sector_written,
                    'len(sector_written)': len(sector_written),
                })

            total_written += sector_written
            s = e

        if id:
            total_written = total_written.strip()
            if self._log.isEnabledFor(logging.DEBUG):
                self._log.debug({
                    'action': 'card written',
                    'id': id,
                    'len(text)': len(text),
                    'text': text,
                    'len(total_written)': len(total_written),
                    'total_written': total_written,
                })
            return id, total_written
        else:
            return None, None
