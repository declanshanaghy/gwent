import asyncio

import hashlib
import os.path
import json
import random
import tempfile
import time
import logging

import gwent.hal
import gwent.messaging.base
import gwent.messaging.cards.card
import gwent.messaging.cards.util

BLOCK_SIZE = 16
SECTOR_SIZE = 4
SECTOR_WRITABLE = 3

MIN_SECTOR = 1
MAX_SECTOR = 15
ALL_SECTORS = range(MIN_SECTOR, MAX_SECTOR + 1)

LOG_FREQ_SECS = 5


def instance():
    if gwent.hal.REAL:
        return _RealWriter()
    else:
        return _FakeWriter()


class RFIDError(Exception):
    pass


class _BaseReader(gwent.hal.Component):
    last_log = 0

    def should_log(self) -> bool:
        r = time.time() > self.last_log + LOG_FREQ_SECS
        if r:
            self.last_log = time.time()
        return r

    def read_card(self) -> gwent.messaging.cards.card.Message:
        start = time.time()
        s_details, id = self.read_card_impl()

        card = None
        if id is not None:
            j_details = json.loads(s_details)
            card = gwent.messaging.cards.card.Message.from_properties(j_details,
                                                                 rfid=id)

        if self.should_log():
            end = time.time()
            elapsed = end - start
            self._log.debug({
                'action': 'read_card',
                'start': start,
                'end': end,
                'success': card is not None,
                'elapsed': elapsed,
            })

        return card

    def read_card_impl(self) -> (str, int):
        raise NotImplementedError('subclass must implement read_card_impl')


class _FakeReader(_BaseReader):
    flag_read_file = os.path.join(tempfile.gettempdir(), 'rfid.read')

    def read_card_impl(self) -> (str, int):
        exists = os.path.exists(self.flag_read_file)
        if exists:
            with open(self.flag_read_file) as f:
                details = f.read()
                id = hashlib.md5(details.encode()).hexdigest()
            os.unlink(self.flag_read_file)
            return details, id
        else:
            return None, None


class _RealReader(_BaseReader):
    _rfid = None

    def __init__(self):
        super().__init__()
        if gwent.hal.REAL:
            import mfrc522
            self._rfid = mfrc522.SimpleMFRC522()

    def read_card_impl(self) -> (str, int):
        header = self._read_card_header()
        if header is not None:
            return self._read_card_body(bytes=header['bytes'])
        else:
            return None, None

    @staticmethod
    def get_blocks(sector: int) -> (int, [int]):
        s = sector * 4
        e = s + 3
        blocks = []
        for b in range(s, e):
            blocks.append(b)
        return e, blocks

    def read_sector(self, trailer: int = 11,
                    blocks: [int] = (8, 9, 10)) -> (int, str):
        id, text, _ = self._rfid.read(trailer=trailer,
                                      blocks=blocks, attempts=3)
        if id:
            text = text.strip()
            return id, text
        else:
            return None, None

    def _read_card_header(self) -> dict:
        # Assumes the header only takes up 1 sector
        header_sector = gwent.messaging.cards.card.Message.header_sector_start()
        trailer, blocks = _RealReader.get_blocks(header_sector)
        id, header = self.read_sector(trailer=trailer, blocks=blocks)

        if id is not None and header is not None:
            last = header.find('}') + 1
            header = json.loads(header[:last])

            self._log.info({
                'action': '_read_card_header',
                'header': header,
            })

        return header

    def _read_card_body(self, bytes: int) -> (str, int):
        sectors = gwent.messaging.cards.card.Message.sector_range(
            gwent.messaging.cards.card.Message.body_sector_start(), bytes)
        body = ""
        id = 0

        debug_enabled = self._log.isEnabledFor(logging.DEBUG)
        start = time.time()

        for sector in sectors:
            trailer, blocks = _RealReader.get_blocks(sector)
            id, sector_data = self.read_sector(trailer=trailer, blocks=blocks)
            if debug_enabled:
                self._log.debug({
                    'action': 'sector read',
                    'sector': sector,
                    'trailer': trailer,
                    'blocks': blocks,
                    'id': id,
                    'sector_data': sector_data,
                    'len(sector_data)': len(sector_data),
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

        # We will have read the entire sector but the JSON
        # will most likely only take up a portion of it.
        # slice to the correct size
        return body[:bytes], id


class _BaseWriter(_BaseReader):
    def write_card(self, card: gwent.messaging.cards.card.Message) -> int:
        start = time.time()
        id = self.write_card_impl(card)

        if id is not None:
            card.rfid = id

        if self.should_log():
            end = time.time()
            elapsed = end - start
            self._log.debug({
                'action': 'write_card',
                'success': card.rfid is not None,
                'rfid': card.rfid,
                'start': start,
                'end': end,
                'elapsed': elapsed,
            })

        return card.rfid

    def write_card_impl(self, card: gwent.messaging.cards.card.Message) -> int:
        raise NotImplementedError('subclass must implement write_card_impl')


class _FakeWriter(_BaseWriter, _FakeReader):
    flag_write_file = os.path.join(tempfile.gettempdir(), 'rfid.write')

    def write_card_impl(self, card: gwent.messaging.cards.card.Message) -> int:
        exists = os.path.exists(self.flag_write_file)
        if exists:
            os.unlink(self.flag_write_file)
            return random.randint(10000000, 999999999)
        else:
            return None


class _RealWriter(_BaseWriter, _RealReader):
    def write_card_impl(self, card: gwent.messaging.cards.card.Message) -> int:
        # import pydevd_pycharm
        # pydevd_pycharm.settrace('192.168.1.143', port=31337,
        #                         stdoutToServer=True, stderrToServer=True)

        id1, _ = self._write_card_header(card)
        if id1 is not None:
            id2, _ = self._write_card_body(card)

            if id1 != id2:
                raise RFIDError(
                    f'Wrote to 2 different cards, id1={id1} id2={id2}')

        return id1

    def _write_card_header(self, card: gwent.messaging.cards.card.Message) -> (
            int, str):
        self._log.debug({
            'action': '_write_card_header',
            'header': card.header,
            'header_sectors': card.header_sectors(),
        })
        return self._write_str(
            card.header, sectors=card.header_sectors())

    def _write_card_body(self, card: gwent.messaging.cards.card.Message) -> (
    int, str):
        self._log.debug({
            'action': '_write_card_body',
            'body': card.body,
            'len(card.body)': len(card.body),
            'sectors': card.body_sectors,
            'num_sectors': len(card.body_sectors),
        })
        return self._write_str(
            card.body, sectors=card.body_sectors)

    def _write_str(self, text: str,
                   sectors: [int] = ALL_SECTORS) -> (int, str):

        id, _ = self._rfid.read_id(attempts=3)
        if id is None:
            return None, None

        self._log.info({
            'action': 'card present',
            'id': id,
        })

        s = 0
        written = ""
        maxlen = len(text)
        debug_enabled = self._log.isEnabledFor(logging.DEBUG)

        for sector in sectors:
            trailer, blocks = _RealReader.get_blocks(sector)
            e1 = s + (SECTOR_WRITABLE * BLOCK_SIZE)
            e = min(maxlen, e1)
            sector_data = text[s:e]

            # Pad with null if len(data) < 16
            if len(sector_data) < BLOCK_SIZE * len(blocks):
                npad = BLOCK_SIZE * len(blocks) - len(sector_data)
                sector_data += "\0" * npad

            id, sector_written, _ = self._rfid.write(
                sector_data, trailer=trailer, blocks=blocks, attempts=3)

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

            written += sector_written
            s = e

        written = written.strip()
        if self._log.isEnabledFor(logging.DEBUG):
            self._log.debug({
                'action': 'string written',
                'id': id,
                'len(text)': len(text),
                'text': text,
                'len(total_written)': len(written),
                'total_written': written,
            })
        return id, written
