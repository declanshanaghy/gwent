import asyncio
import hashlib
import os.path
import json
import random
import tempfile
import time
import logging

import RPi.GPIO as GPIO

import gwent.hal
import gwent.game
import gwent.messaging.base
import gwent.messaging.card
import gwent.cards.util

BLOCK_SIZE = 16
SECTOR_SIZE = 4
SECTOR_WRITABLE = 3

MIN_SECTOR = 1
MAX_SECTOR = 15
ALL_SECTORS = range(MIN_SECTOR, MAX_SECTOR + 1)

MAX_ATTEMPTS = 2


async def instance(loop: asyncio.AbstractEventLoop):
    if await gwent.hal.real_mode():
        return _RealWriter(loop, log_verbose=False)
    else:
        return _FakeWriter(loop)


class RFIDError(Exception):
    pass


class _BaseReader(gwent.game.GameComponent):
    def read_card(self) -> gwent.messaging.card.Message:
        should_log = self.should_log()

        start = time.time()
        id, s_details = self.read_card_impl(should_log)

        card = None
        if id is not None and s_details is not None:
            j_details = json.loads(s_details)
            card = gwent.messaging.card.Message.from_properties(j_details,
                                                                rfid=id)
        if should_log or card is not None:
            self.log_time('read_card', start)

        return card

    def read_card_impl(self, should_log: bool) -> (int, str):
        raise NotImplementedError('subclass must implement read_card_impl')


class _FakeReader(_BaseReader):
    flag_read_file = os.path.join(tempfile.gettempdir(), 'rfid.read')

    def __init__(self, loop: asyncio.AbstractEventLoop, log_verbose: bool = False):
        super().__init__(loop, log_verbose=log_verbose)
        self._log.debug({'flag_read_file': self.flag_read_file})

    def read_card_impl(self, should_log: bool) -> (int, str):
        exists = os.path.exists(self.flag_read_file)
        if should_log:
            self._log.debug({
                'action': 'read_card_impl',
                'flag_read_file': self.flag_read_file,
                'exists': exists,
            })
        if exists:
            with open(self.flag_read_file) as f:
                details = f.read()
                id = hashlib.md5(details.encode()).hexdigest()
            os.unlink(self.flag_read_file)
            return id, details
        else:
            return None, None


class _RealReader(_BaseReader):
    _rfid = None

    def __init__(self, loop: asyncio.AbstractEventLoop, log_verbose: bool = False):
        super().__init__(loop, log_verbose=log_verbose)

        def setup():
            import mfrc522
            self._rfid = mfrc522.SimpleMFRC522(log_verbose=log_verbose, pin_mode=GPIO.BCM)

        self._loop.run_in_executor(None, setup)

    def read_card_impl(self, should_log: bool) -> (int, str):
        id, header = self._read_card_header()
        if header is not None:
            id, body = self._read_card_body(bytes=header['bytes'])
            if id is None:
                self._log.error({
                    'action': 'read card body failed',
                })
                return None, None
            return id, body
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
        id, text, _ = self._rfid.read(
            trailer=trailer, blocks=blocks, attempts=MAX_ATTEMPTS)
        if id:
            text = text.strip()
            return id, text
        else:
            return None, None

    def _read_card_header(self) -> (int, dict):
        start = time.time()
        # Assumes the header only takes up 1 sector
        header_sector = gwent.messaging.card.Message.header_sector_start()
        trailer, blocks = _RealReader.get_blocks(header_sector)
        id, header = self.read_sector(trailer=trailer, blocks=blocks)

        if id is not None and header is not None:
            last = header.find('}') + 1
            header = json.loads(header[:last])
            self.log_time('read card header', start)

        return id, header

    def _read_card_body(self, bytes: int) -> (int, str):
        sectors = gwent.messaging.card.Message.sector_range(
            gwent.messaging.card.Message.body_sector_start(), bytes)
        body = ""
        id = None

        debug_enabled = self._log.isEnabledFor(logging.DEBUG)
        body_start = time.time()

        for sector in sectors:
            sector_start = time.time()
            trailer, blocks = _RealReader.get_blocks(sector)
            id, sector_data = self.read_sector(trailer=trailer, blocks=blocks)
            if id is None:  # The card was removed
                return None, None

            end = time.time()
            if debug_enabled:
                self._log.debug({
                    'action': 'read sector',
                    'sector': sector,
                    'trailer': trailer,
                    'blocks': blocks,
                    'id': id,
                    'sector_data': sector_data,
                    'start': sector_start,
                    'end': end,
                    'duration': end - sector_start,
                })
            body += sector_data

        self.log_time('read card body', body_start)

        # We will have read the entire sector but the JSON
        # will most likely only take up a portion of it.
        # slice to the correct size
        return id, body[:bytes]


class _BaseWriter(_BaseReader):
    def write_card(self, card: gwent.messaging.card.Message) -> int:
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

    def write_card_impl(self, card: gwent.messaging.card.Message) -> int:
        raise NotImplementedError('subclass must implement write_card_impl')


class _FakeWriter(_BaseWriter, _FakeReader):
    flag_write_file = os.path.join(tempfile.gettempdir(), 'rfid.write')

    def __init__(self, loop: asyncio.AbstractEventLoop, log_verbose: bool = False):
        super().__init__(loop, log_verbose=log_verbose)
        self._log.debug({'flag_write_file': self.flag_write_file})

    def write_card_impl(self, card: gwent.messaging.card.Message) -> int:
        exists = os.path.exists(self.flag_write_file)
        if exists:
            os.unlink(self.flag_write_file)
            return random.randint(10000000, 999999999)
        else:
            return None


class _RealWriter(_BaseWriter, _RealReader):
    def write_card_impl(self, card: gwent.messaging.card.Message) -> int:
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

    def _write_card_header(self, card: gwent.messaging.card.Message) -> (
            int, str):
        self._log.debug({
            'action': '_write_card_header',
            'header': card.header,
            'header_sectors': card.header_sectors(),
        })
        return self._write_str(
            card.header, sectors=card.header_sectors())

    def _write_card_body(self, card: gwent.messaging.card.Message) -> (
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

        id, _ = self._rfid.read_id(attempts=MAX_ATTEMPTS)
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
                sector_data, trailer=trailer, blocks=blocks,
                attempts=MAX_ATTEMPTS)

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
