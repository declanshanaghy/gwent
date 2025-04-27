import hashlib
import os.path
import json
import random
import tempfile
import time
import logging
import threading

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


def instance():
    if gwent.hal.real_mode():
        return RealWriter(log_verbose=False)
    else:
        return _FakeWriter()


class RFIDError(Exception):
    pass


class _BaseReader(gwent.game.BaseComponent):
    def read_card(self) -> gwent.messaging.card.Message:
        should_log = self.should_log()

        start = time.time()
        id, s_details = self.read_card_impl(should_log)

        card = None
        if id is not None:
            # If we have an ID but no details, it's a blank card
            if s_details is None or not s_details.strip():
                self._log.info({
                    'action': 'blank_or_uninitialized_card',
                    'id': id,
                    'message': 'Card detected but appears to be blank or uninitialized'
                })
                # Create a minimal card with just the RFID
                card = gwent.messaging.card.Message.from_properties(rfid=id)
            else:
                try:
                    # Check if the string contains valid JSON
                    if '{' in s_details and '}' in s_details:
                        j_details = json.loads(s_details)
                        # Ensure the RFID is included
                        if 'rfid' not in j_details:
                            j_details['rfid'] = id
                        card = gwent.messaging.card.Message.from_properties(j_details)
                    else:
                        self._log.warning({
                            'action': 'invalid_card_data',
                            'id': id,
                            'reason': 'No JSON content found',
                            'data': s_details[:50] + ('...' if len(s_details) > 50 else '')
                        })
                        # Create a minimal card with just the RFID
                        card = gwent.messaging.card.Message.from_properties(rfid=id)
                except json.JSONDecodeError as e:
                    self._log.warning({
                        'action': 'json_decode_error_in_card_data',
                        'id': id,
                        'error': str(e),
                        'data': s_details[:50] + ('...' if len(s_details) > 50 else '')
                    })
                    # Create a minimal card with just the RFID
                    card = gwent.messaging.card.Message.from_properties(rfid=id)
                except Exception as e:
                    self._log.error({
                        'action': 'unexpected_error_parsing_card_data',
                        'id': id,
                        'error': str(e),
                        'data': s_details[:50] + ('...' if len(s_details) > 50 else '')
                    })
                    # Create a minimal card with just the RFID
                    card = gwent.messaging.card.Message.from_properties(rfid=id)
                
        if should_log or card is not None:
            self.log_time('read_card', start)

        return card

    def read_card_impl(self, should_log: bool) -> (int, str):
        raise NotImplementedError('subclass must implement read_card_impl')


class _FakeReader(_BaseReader):
    flag_read_file = os.path.join(tempfile.gettempdir(), 'rfid.read')

    def __init__(self, log_verbose: bool = False):
        super().__init__(log_verbose=log_verbose)
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

    def __init__(self, log_verbose: bool = False):
        super().__init__(log_verbose=log_verbose)
        self._setup_rfid(log_verbose)

    def _setup_rfid(self, log_verbose):
        import mfrc522
        try:
            # Try with both parameters
            self._rfid = mfrc522.SimpleMFRC522(log_verbose=log_verbose, pin_mode=GPIO.BCM)
        except TypeError:
            try:
                # Try with just log_verbose
                self._rfid = mfrc522.SimpleMFRC522(log_verbose=log_verbose)
            except TypeError:
                try:
                    # Try with just pin_mode
                    self._rfid = mfrc522.SimpleMFRC522(pin_mode=GPIO.BCM)
                except TypeError:
                    # Fall back to no parameters
                    self._rfid = mfrc522.SimpleMFRC522()

    def read_card_impl(self, should_log: bool) -> (int, str):
        self._log.info({
            'action': 'starting card read',
            'timestamp': time.time()
        })
        
        # First check if a card is physically present by reading its ID
        id, _ = self._rfid.read_id(attempts=3)
        if id is None:
            self._log.warning({
                'action': 'no card detected',
                'timestamp': time.time()
            })
            return None, None
            
        self._log.info({
            'action': 'card detected',
            'id': id,
            'timestamp': time.time()
        })
        
        # Try to read the header
        id, header = self._read_card_header()
        
        # If header read fails, this is likely a blank card
        if header is None:
            self._log.info({
                'action': 'blank card detected',
                'id': id,
                'timestamp': time.time()
            })
            # Return the ID but no details to indicate a blank card
            return id, None
            
        self._log.info({
            'action': 'read card header success',
            'id': id,
            'header': header
        })
        
        # Add a longer delay before reading the body
        time.sleep(1.5)
        
        # Add retry logic for body reads
        max_body_attempts = 2  # Reduced from 3 to 2
        body = None
        
        for attempt in range(1, max_body_attempts + 1):
            self._log.info({
                'action': 'attempting card body read',
                'attempt': attempt,
                'max_attempts': max_body_attempts
            })
            
            id, body = self._read_card_body(n_bytes=header['bytes'])
            
            if id is not None and body is not None:
                break
                
            if attempt < max_body_attempts:
                self._log.warning({
                    'action': 'retrying card body read',
                    'attempt': attempt,
                    'timestamp': time.time()
                })
                # Reset reader between attempts
                if hasattr(self, 'reset') and callable(self.reset):
                    self.reset()
                time.sleep(1.0)  # Longer delay between retry attempts
        
        if id is None or body is None:
            self._log.error({
                'action': 'read card body failed after all attempts',
                'timestamp': time.time()
            })
            # Try to reset the reader before returning
            if hasattr(self, 'reset') and callable(self.reset):
                self._log.info("Resetting RFID reader after failed body read")
                self.reset()
                time.sleep(1.0)  # Add a longer delay after reset
            # Return the ID but no details to indicate a blank card
            return id, None
        
        self._log.info({
            'action': 'read card body success',
            'id': id,
            'body_length': len(body) if body else 0
        })
        
        return id, body

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
        self._log.debug({
            'action': 'read_sector',
            'trailer': trailer,
            'blocks': blocks
        })
        
        # Add a small delay before reading
        time.sleep(0.05)
        
        id, text, _ = self._rfid.read(
            trailer=trailer, blocks=blocks, attempts=MAX_ATTEMPTS)
            
        if id:
            text = text.strip()
            self._log.debug({
                'action': 'read_sector_success',
                'id': id,
                'text_length': len(text) if text else 0
            })
            return id, text
        else:
            self._log.debug({
                'action': 'read_sector_failed',
                'trailer': trailer,
                'blocks': blocks
            })
            return None, None

    def _read_card_header(self) -> (int, dict):
        start = time.time()
        # Assumes the header only takes up 1 sector
        header_sector = gwent.messaging.card.Message.header_sector_start()
        trailer, blocks = _RealReader.get_blocks(header_sector)
        id, header = self.read_sector(trailer=trailer, blocks=blocks)

        if id is not None and header is not None:
            try:
                # Check if header contains any JSON data
                if '{' in header and '}' in header:
                    last = header.find('}') + 1
                    header = json.loads(header[:last])
                    self.log_time('read card header', start)
                else:
                    self._log.warning({
                        'action': 'invalid_header_format',
                        'header': header,
                        'reason': 'No JSON brackets found'
                    })
                    # Return None for header to indicate invalid format
                    header = None
            except json.JSONDecodeError as e:
                self._log.warning({
                    'action': 'json_decode_error',
                    'error': str(e),
                    'header': header
                })
                # Return None for header to indicate parsing failure
                header = None
            except Exception as e:
                self._log.error({
                    'action': 'unexpected_error_parsing_header',
                    'error': str(e),
                    'header': header
                })
                # Return None for header to indicate parsing failure
                header = None

        return id, header

    def _read_card_body(self, n_bytes: int) -> (int, str):
        sectors = gwent.messaging.card.Message.sector_range(
            gwent.messaging.card.Message.body_sector_start(), n_bytes)
        body = ""
        id = None

        debug_enabled = self._log.isEnabledFor(logging.DEBUG)
        body_start = time.time()
        
        self._log.info({
            'action': 'starting card body read',
            'n_bytes': n_bytes,
            'sectors_to_read': list(sectors)
        })

        for sector in sectors:
            sector_start = time.time()
            self._log.info({
                'action': 'reading sector',
                'sector': sector
            })
            
            # Add a longer delay before reading each sector
            time.sleep(0.5)  # Increased from 0.3 to 0.5
            
            # Try multiple times to read each sector
            max_sector_attempts = 3  # Increased from 2 to 3
            sector_data = None
            
            for attempt in range(1, max_sector_attempts + 1):
                trailer, blocks = _RealReader.get_blocks(sector)
                id, sector_data = self.read_sector(trailer=trailer, blocks=blocks)
                
                if id is not None and sector_data is not None:
                    break
                    
                if attempt < max_sector_attempts:
                    self._log.warning({
                        'action': 'retrying sector read',
                        'sector': sector,
                        'attempt': attempt
                    })
                    time.sleep(0.5)  # Increased from 0.3 to 0.5
            
            if id is None:  # The card was removed or read failed
                self._log.error({
                    'action': 'read card body failed',
                    'sector': sector
                })
                # Try to reset the reader before returning
                if hasattr(self, 'reset') and callable(self.reset):
                    self._log.info("Resetting RFID reader after failed read")
                    self.reset()
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
            
            # Add a longer delay after reading each sector
            time.sleep(0.8)  # Increased from 0.5 to 0.8

        self.log_time('read card body', body_start)
        
        self._log.info({
            'action': 'completed card body read',
            'body_length': len(body),
            'n_bytes': n_bytes,
            'duration': time.time() - body_start
        })

        # We will have read the entire sector but the JSON
        # will most likely only take up a portion of it.
        # slice to the correct size
        return id, body[:n_bytes]


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

    def __init__(self, log_verbose: bool = False):
        super().__init__(log_verbose=log_verbose)
        self._log.debug({'flag_write_file': self.flag_write_file})

    def write_card_impl(self, card: gwent.messaging.card.Message) -> int:
        exists = os.path.exists(self.flag_write_file)
        if exists:
            os.unlink(self.flag_write_file)
            return random.randint(10000000, 999999999)
        else:
            return None


class RealWriter(_BaseWriter, _RealReader):
    def reset(self):
        """Reset the RFID reader to ensure it's in a clean state"""
        self._log.info({
            'action': 'resetting_rfid_reader',
            'timestamp': time.time()
        })
        
        try:
            # Try to re-initialize the RFID reader
            # Use False for log_verbose since we're already logging the reset
            self._setup_rfid(log_verbose=False)
            
            # Add a longer delay after reset
            time.sleep(1.0)
            
            # Try to read the ID to ensure the reader is working
            id, _ = self._rfid.read_id(attempts=1)
            if id is not None:
                self._log.info({
                    'action': 'rfid_reader_reset_complete_with_card_present',
                    'id': id,
                    'timestamp': time.time()
                })
            else:
                self._log.info({
                    'action': 'rfid_reader_reset_complete_no_card_detected',
                    'timestamp': time.time()
                })
            
            return True
        except Exception as e:
            self._log.error({
                'action': 'rfid_reader_reset_failed',
                'error': str(e),
                'timestamp': time.time()
            })
            return False
    
    def write_card_impl(self, card: gwent.messaging.card.Message) -> int:
        # Reset the reader before writing
        self.reset()
        
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

            # Check if sector_written is None before concatenating
            if sector_written is not None:
                written += sector_written
            else:
                self._log.error({
                    'action': 'sector write failed',
                    'sector': sector,
                    'id': id
                })
                # Return None to indicate write failure
                return None, None
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
