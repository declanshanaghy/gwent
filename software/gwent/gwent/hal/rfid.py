import json
import random
import time
import logging

import gwent.game.cards
import gwent.game.cards.all
import gwent.log

BLOCK_SIZE = 16
SECTOR_SIZE = 4
SECTOR_WRITABLE = 3

MIN_SECTOR = 1
MAX_SECTOR = 15
ALL_SECTORS = range(MIN_SECTOR, MAX_SECTOR + 1)


class RFIDError(Exception):
    pass


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

    @staticmethod
    def get_blocks(sector: int) -> (int, [int]):
        s = sector * 4
        e = s + 3
        blocks = []
        for b in range(s, e):
            blocks.append(b)
        return e, blocks

    def read_sector(self, block: bool = False, trailer: int = 11,
                    blocks: [int] = (8, 9, 10)) -> (int, str, int):
        if self._rfid is not None:
            id, text, tries = self.read_real(block=block, trailer=trailer,
                                             blocks=blocks)
        else:
            id, text, tries = self.read_fake()

        if id:
            return id, text, tries
        else:
            raise RFIDError(f'Error reading sector: '
                            f'trailer={trailer}, blocks={blocks}')

    def read_fake(self) -> (int, str, int):
        t = float(random.randint(0, 100)) / 100
        self._log.info(f'Will produce a fake tag in {t} seconds')
        time.sleep(t)
        details = gwent.game.cards.all.random_card_details()
        return random.randint(10000000, 999999999), json.dumps(details), 1

    def read_real(self, block: bool = False, trailer: int = 11,
                  blocks: [int] = (8, 9, 10)) -> (int, str, int):
        if block:
            id, text, tries = self._rfid.read(trailer=trailer, blocks=blocks,
                                              attempts=10)
        else:
            id, text, tries = self._rfid.read_no_block(trailer=trailer,
                                                       blocks=blocks)
        if id:
            text = text.strip()
            return id, text, tries
        else:
            return None, None, None

    def _read_card_header(self, block: bool = False) -> dict:
        if self._rfid is not None:
            # Assumes the header only takes up 1 sector
            header_sector = gwent.game.cards.Card.header_sector_start()
            trailer, blocks = Reader.get_blocks(header_sector)
            id, header, tries = self.read_sector(
                block=block, trailer=trailer, blocks=blocks)
            last = header.find('}') + 1
            header = json.loads(header[:last])
        else:
            # Must be 48 or less, so only 1 fake sector is read
            header = {"bytes": 48}

        self._log.info({
            'action': '_read_card_header',
            'header': header,
        })

        return header

    def _read_card_body(self, bytes: int, block: bool = False) -> (dict, int):
        sectors = gwent.game.cards.Card.sector_range(
            gwent.game.cards.Card.body_sector_start(), bytes)
        body = ""
        id = 0

        debug_enabled = self._log.isEnabledFor(logging.DEBUG)
        start = time.time()

        self._log.info({
            'action': '_read_card_body',
            'stage': 'start',
            'start': start,
            'bytes': bytes,
            'sectors': sectors,
        })

        for sector in sectors:
            trailer, blocks = Reader.get_blocks(sector)
            id, sector_data, tries = self.read_sector(
                block=block, trailer=trailer, blocks=blocks)
            if debug_enabled:
                self._log.debug({
                    'action': 'sector read',
                    'sector': sector,
                    'trailer': trailer,
                    'blocks': blocks,
                    'id': id,
                    'sector_data': sector_data,
                    'len(sector_data)': len(sector_data),
                    'tries': tries,
                })
            body += sector_data

        end = time.time()
        elapsed = end - start
        self._log.info({
            'action': '_read_card_body',
            'stage': 'end',
            'elapsed': elapsed,
            'end': end,
        })

        if self._rfid is not None:
            # In real mode we will have read the entire sector but the JSON
            # will most likely only take up a portion of it.
            # slice to the correct size
            trunc = body[:bytes]
            self._log.debug({
                'action': 'truncate body',
                'body': body,
                'trunc': trunc,
                'bytes': bytes,
            })
            body = trunc

        return json.loads(body), id

    def read_card(self, block: bool = False) -> gwent.game.cards.Card:
        start = time.time()
        self._log.info({
            'action': 'read_card',
            'stage': 'start',
            'start': start,
        })

        header = self._read_card_header(block=block)
        details, id = self._read_card_body(block=block, bytes=header['bytes'])

        end = time.time()
        elapsed = end - start

        card = gwent.game.cards.Card(details, id=id)

        self._log.info({
            'action': 'read_card',
            'stage': 'end',
            'id': card.id,
            'name': card.name,
            'start': start,
            'end': end,
            'elapsed': elapsed,
        })

        return card


class Writer(Reader):
    def write_sector(self, text: str, block: bool = False,
                     trailer: int = 11,
                     blocks: [int] = (8, 9, 10)) -> (int, str, int):
        if self._rfid is not None:
            if block:
                id, text, tries = self._rfid.write(text, trailer=trailer,
                                                   blocks=blocks, attempts=10)
            else:
                id, text, tries = self._rfid.write_no_block(
                    text, trailer=trailer, blocks=blocks)
        else:
            id, text, tries = self._write_fake(text, block=block,
                                               trailer=trailer, blocks=blocks)

        if id:
            return id, text, tries
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
        return id, text, 1

    def write_card(self, card: gwent.game.cards.Card,
                   block: bool = False) -> int:

        start = time.time()
        self._log.info({
            'action': 'write_card',
            'stage': 'start',
            'id': card.id,
            'start': start,
        })

        id1, _, _ = self._write_card_header(card, block=block)
        id2, _, _ = self._write_card_body(card, block=block)

        if self._rfid is not None and id1 != id2:
            raise RFIDError(f'Wrote to 2 different cards, id1={id1} id2={id2}')

        card.id = id1

        end = time.time()
        elapsed = end - start
        self._log.info({
            'action': 'write_card',
            'stage': 'end',
            'id': card.id,
            'start': start,
            'end': end,
            'elapsed': elapsed,
        })

        return id1

    def _write_card_header(self, card: gwent.game.cards.Card,
                           block: bool = False) -> (int, str, int):
        self._log.info({
            'action': '_write_card_header',
            'header': card.header,
            'header_sectors': card.header_sectors,
        })
        return self._write_str(
            card.header, block=block, sectors=card.header_sectors())

    def _write_card_body(self, card: gwent.game.cards.Card,
                         block: bool = False) -> (int, str, int):
        self._log.info({
            'action': '_write_card_body',
            'body': card.body,
            'len(card.body)': len(card.body),
            'sectors': card.body_sectors,
            'num_sectors': len(card.body_sectors),
        })

        return self._write_str(
            card.body, block=block, sectors=card.body_sectors)

    def _write_str(self, text: str, block: bool = False,
                   sectors: [int] = None) -> (int, str, int):
        if sectors is None:
            sectors = ALL_SECTORS
        id = None
        total_written = ""
        total_tries = 0

        debug_enabled = self._log.isEnabledFor(logging.DEBUG)

        maxlen = len(text)
        s = 0
        for sector in sectors:
            trailer, blocks = Reader.get_blocks(sector)
            e1 = s + (SECTOR_WRITABLE * BLOCK_SIZE)
            e = min(maxlen, e1)
            sector_data = text[s:e]

            # Pad with null if len(data) < 16
            if len(sector_data) < BLOCK_SIZE * len(blocks):
                npad = BLOCK_SIZE * len(blocks) - len(sector_data)
                sector_data += "\0" * npad

            id, sector_written, tries = self.write_sector(
                sector_data, block=block, trailer=trailer, blocks=blocks)

            if debug_enabled:
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
            total_tries += tries
            s = e

        if id:
            total_written = total_written.strip()
            if self._log.isEnabledFor(logging.DEBUG):
                self._log.debug({
                    'action': 'string written',
                    'id': id,
                    'len(text)': len(text),
                    'text': text,
                    'len(total_written)': len(total_written),
                    'total_written': total_written,
                })
            return id, total_written, total_tries
        else:
            return None, None, None
