import os.path
import json
import random
import time
import threading
import traceback
import mfrc522

import RPi.GPIO as GPIO

from gwent.utils.logging import get_logger, DEBUG

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
    return RealWriter()


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
                # The hardware layer should not access the database
                # Upper layers will handle database lookups based on the RFID
                card = gwent.messaging.card.Message.from_properties(rfid=id)
                self._log.info({
                    'action': 'created_blank_card',
                    'id': id,
                    'message': 'Card detected but appears to be blank or uninitialized'
                })
            else:
                try:
                    # Ensure to strip all trailing null bytes
                    s_details = s_details.rstrip('\x00')
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
                            's_details': s_details
                        })
                        # Create a minimal card with just the RFID
                        card = gwent.messaging.card.BlankCardMessage.from_properties(rfid=id)
                except json.JSONDecodeError as e:
                    self._log.error({
                        'action': 'json_decode_error_in_card_data',
                        'id': id,
                        'error': str(e),
                        's_details': s_details
                    })
                    # Create a minimal card with just the RFID
                    card = gwent.messaging.card.BlankCardMessage.from_properties(rfid=id)
                except Exception as e:
                    self._log.error({
                        'action': 'unexpected_error_parsing_card_data',
                        'id': id,
                        'error': str(e),
                        'error_traceback': traceback.format_exc(),
                        's_details': s_details
                    })
                    # Create a minimal card with just the RFID
                    card = gwent.messaging.card.Message.from_properties(rfid=id)
                
        if should_log or card is not None:
            self.log_time('read_card', start)

        return card

    def read_card_impl(self, should_log: bool) -> (int, str):
        raise NotImplementedError('subclass must implement read_card_impl')


class _RealReader(_BaseReader):
    _rfid = None

    def __init__(self):
        super().__init__()
        self._setup_rfid()
        self._log.debug({
            'action': 'rfid_reader_initialized'
        })

    def _setup_rfid(self):
        self._log.debug({
            'action': 'setup_rfid_start'
        })
        
        self._rfid = mfrc522.SimpleMFRC522(pin_mode=GPIO.BCM)
        self._log.debug({'rfid_init': 'mfrc522.SimpleMFRC522 pin_mode=GPIO.BCM'})

    def read_card_impl(self, should_log: bool) -> (int, str):
        self._log.debug({'action': 'spi_lock_rfid_waiting'})
        lock_wait_start = time.time()
        acquired = gwent.hal.spi_lock.acquire(timeout=2.0)
        lock_wait = time.time() - lock_wait_start
        if not acquired:
            self._log.warning({
                'action': 'spi_lock_rfid_timeout',
                'waited': f'{lock_wait:.3f}s',
            })
            return None, None
        self._log.debug({
            'action': 'spi_lock_rfid_acquired',
            'waited': f'{lock_wait:.3f}s',
        })
        try:
            result = self._read_card_locked(should_log)
            return result
        finally:
            held = time.time() - lock_wait_start - lock_wait
            self._log.debug({
                'action': 'spi_lock_rfid_released',
                'held': f'{held:.3f}s',
            })
            gwent.hal.spi_lock.release()

    def _read_card_locked(self, should_log: bool) -> (int, str):
        start_time = time.time()
        self._log.debug({
            'action': 'starting card read',
            'timestamp': start_time
        })

        # Re-assert antenna on — shared SPI bus with OLED
        self._rfid._mfrc522.AntennaOn()

        # First check if a card is physically present by reading its ID
        read_id_start = time.time()
        original_id, _ = self._rfid.read_id(attempts=10)
        read_id_duration = time.time() - read_id_start
        
        if original_id is None:
            if should_log:
                self._log.info({
                    'action': 'no card detected',
                    'read_id_duration': f'{read_id_duration:.3f}'
                })
            return None, None
            
        self._log.info({
            'action': 'card detected',
            'original_id': original_id,
            'timestamp': time.time(),
            'read_id_duration': read_id_duration
        })
        
        # Try to read the header
        header_start = time.time()
        self._log.debug({
            'action': 'starting_header_read',
            'timestamp': header_start
        })
        id, header = self._read_card_header(original_id)
        header_duration = time.time() - header_start
        
        # If header read fails but we have the original ID, use that
        if header is None:
            if id is None and original_id is not None:
                self._log.warning({
                    'action': 'header_read_failed_using_original_id',
                    'original_id': original_id,
                    'timestamp': time.time(),
                    'header_read_attempt_duration': header_duration
                })
                id = original_id
                
            self._log.warning({
                'action': 'blank card detected',
                'id': id,
                'original_id': original_id,
                'timestamp': time.time(),
                'header_read_attempt_duration': header_duration,
                'possible_cause': 'Header read failed or could not be parsed as JSON'
            })
            # Return the ID but no details to indicate a blank card
            return id, None
            
        self._log.debug({
            'action': 'read card header success',
            'id': id,
            'header': header,
            'header_read_duration': header_duration
        })
        
        # No need for delay before reading the body - card_manager handles retries
        self._log.debug({
            'action': 'starting_body_read'
        })
        
        # Add retry logic for body reads
        max_body_attempts = 2  # Reduced from 3 to 2
        body = None
        
        for attempt in range(1, max_body_attempts + 1):
            body_read_start = time.time()
            self._log.info({
                'action': 'attempting card body read',
                'attempt': attempt,
                'max_attempts': max_body_attempts,
                'timestamp': body_read_start
            })
            
            id, body = self._read_card_body(n_bytes=header['bytes'])
            body_read_duration = time.time() - body_read_start
            
            if id is not None and body is not None:
                self._log.debug({
                    'action': 'body_read_success',
                    'attempt': attempt,
                    'body': body,
                    'duration': body_read_duration
                })
                break
                
            if attempt < max_body_attempts:
                self._log.debug({
                    'action': 'retrying card body read',
                    'attempt': attempt,
                    'timestamp': time.time(),
                    'body_read_duration': body_read_duration
                })
                # Reset reader between attempts
                reset_start = time.time()
                if hasattr(self, 'reset') and callable(self.reset):
                    reset_success = self.reset()
                    self._log.debug({
                        'action': 'reset_between_attempts',
                        'success': reset_success,
                        'duration': time.time() - reset_start
                    })
                # No need for delay between retry attempts - card_manager handles retries
        
        if id is None or body is None:
            self._log.debug({
                'action': 'read card body failed after all attempts',
                'timestamp': time.time(),
                'original_id': original_id
            })
            
            # If we have the original ID but the body read failed completely,
            # create a minimal valid body
            if original_id is not None:
                self._log.warning({
                    'action': 'body_read_failed_using_original_id',
                    'original_id': original_id
                })
                # Return the ID but no details to indicate a blank card
                return original_id, None
                
            # Return the ID but no details to indicate a blank card
            return id, None
        
        self._log.debug({
            'action': 'read card body success',
            'id': id,
            'body': body,
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
        self._log.debug({  # Upgraded to INFO for better visibility
            'action': 'read_sector_start',
            'trailer': trailer,
            'blocks': blocks,
            'timestamp': time.time()
        })
        
        # No need for delay before reading - card_manager handles retries
        
        # Store the original ID for comparison
        original_id = None
        try:
            # First check if a card is physically present by reading its ID
            original_id, _ = self._rfid.read_id(attempts=1)
            self._log.debug({
                'action': 'read_sector_id_check',
                'original_id': original_id,
                'timestamp': time.time()
            })
        except Exception as e:
            self._log.error({
                'action': 'read_sector_id_check_error',
                'error': str(e),
                'error_type': type(e).__name__,
                'error_traceback': traceback.format_exc(),
                'timestamp': time.time()
            })
        
        read_start = time.time()
        try:
            id, text, raw_data = self._rfid.read(
                trailer=trailer, blocks=blocks, attempts=MAX_ATTEMPTS)
            
            # Log raw data for debugging
            self._log.debug({
                'action': 'read_sector_raw_data',
                'raw_data_type': type(raw_data).__name__ if raw_data is not None else None,
                'raw_data_length': len(raw_data) if raw_data is not None and hasattr(raw_data, '__len__') else 0,
                'raw_data_sample': str(raw_data)[:100] if raw_data is not None else None
            })
        except Exception as e:
            self._log.error({
                'action': 'read_sector_exception',
                'error': str(e),
                'error_type': type(e).__name__,
                'error_traceback': traceback.format_exc(),
                'trailer': trailer,
                'blocks': blocks,
                'timestamp': time.time()
            })
            return None, None
            
        read_duration = time.time() - read_start
            
        if id:
            text = text.strip() if text else ""
            self._log.debug({  # Upgraded to INFO for better visibility
                'action': 'read_sector_success',
                'id': id,
                'original_id': original_id,
                'id_match': id == original_id,
                'text_length': len(text) if text else 0,
                'text_sample': repr(text[:50]) if text else None,
                'text_bytes': [ord(c) for c in text[:20]] if text else [],
                'duration': read_duration
            })
            return id, text
        else:
            self._log.debug({
                'action': 'read_sector_failed',
                'trailer': trailer,
                'blocks': blocks,
                'original_id': original_id,
                'duration': read_duration,
                'possible_cause': 'Card may have been removed during read or hardware communication issue'
            })
            
            # If we have the original ID but the sector read failed, try to return the ID anyway
            # This might help with cards that have a valid ID but corrupted sectors
            if original_id is not None:
                self._log.warn({
                    'action': 'using_original_id_despite_read_failure',
                    'original_id': original_id
                })
                return original_id, ""
                
            return None, None

    def _read_card_header(self, original_id: int) -> (int, dict):
        start = time.time()
        # Assumes the header only takes up 1 sector
        header_sector = gwent.messaging.card.Message.header_sector_start()
        trailer, blocks = _RealReader.get_blocks(header_sector)
        
        self._log.debug({  # Upgraded to INFO for better visibility
            'action': 'read_card_header_start',
            'header_sector': header_sector,
            'trailer': trailer,
            'blocks': blocks,
            'original_id': original_id,
            'timestamp': start
        })
        
        id, header = self.read_sector(trailer=trailer, blocks=blocks)
        if id is None or header is None:
            self._log.warning({
                'action': 'header_read_failed_using_original_id',
                'original_id': original_id,
                'id': original_id,
                'header': header,
                'timestamp': time.time()
            })
            return None, None

        # Log the raw header data for debugging
        self._log.debug({
            'action': 'read_card_header_raw',
            'id': id,
            'header': header,
            'raw_header': repr(header) if header is not None else None,
            'header_length': len(header) if header is not None else 0,
            'header_type': type(header).__name__ if header is not None else None,
            'header_bytes': [ord(c) for c in header[:20]] if header is not None else None
        })

        if id is not None and header is not None:
            try:
                # Check if header contains any JSON data
                if '{' in header and '}' in header:
                    last = header.find('}') + 1
                    self._log.debug({
                        'action': 'json_extraction',
                        'json_start': header.find('{'),
                        'json_end': last,
                        'extracted_json': header[:last]
                    })
                    header = json.loads(header[:last])
                    self.log_time('read card header', start)
                    self._log.debug({
                        'action': 'parsed_header_json',
                        'parsed_header': header
                    })
                else:
                    self._log.warning({
                        'action': 'invalid_header_format',
                        'header': repr(header),
                        'reason': 'No JSON brackets found',
                        'header_ascii': [ord(c) for c in header[:50]] if header else []
                    })
                    # Return None for header to indicate invalid format
                    header = None
            except json.JSONDecodeError as e:
                self._log.warning({
                    'action': 'json_decode_error',
                    'error': str(e),
                    'error_position': e.pos if hasattr(e, 'pos') else 'unknown',
                    'header': repr(header),
                    'header_substring': repr(header[max(0, e.pos-10):min(len(header), e.pos+10)]) if hasattr(e, 'pos') and header else None
                })
                # Return None for header to indicate parsing failure
                header = None
            except Exception as e:
                self._log.error({
                    'action': 'unexpected_error_parsing_header',
                    'error': str(e),
                    'error_type': type(e).__name__,
                    'error_traceback': traceback.format_exc(),
                    'header': repr(header)
                })
                # Return None for header to indicate parsing failure
                header = None

        return id, header

    def _read_card_body(self, n_bytes: int) -> (int, str):
        sectors = gwent.messaging.card.Message.sector_range(
            gwent.messaging.card.Message.body_sector_start(), n_bytes)
        body = ""
        id = None
        original_id = None

        # First check if a card is physically present by reading its ID
        try:
            original_id, _ = self._rfid.read_id(attempts=1)
            self._log.debug({
                'action': 'body_read_id_check',
                'original_id': original_id,
                'timestamp': time.time()
            })
        except Exception as e:
            self._log.error({
                'action': 'body_read_id_check_error',
                'error': str(e),
                'error_traceback': traceback.format_exc(),
                'timestamp': time.time()
            })

        debug_enabled = self._log.isEnabledFor(DEBUG)
        body_start = time.time()
        
        self._log.debug({
            'action': 'starting card body read',
            'n_bytes': n_bytes,
            'sectors_to_read': list(sectors),
            'timestamp': body_start,
            'original_id': original_id
        })

        for sector in sectors:
            sector_start = time.time()
            self._log.debug({
                'action': 'reading sector',
                'sector': sector,
                'timestamp': sector_start
            })
            
            # No need for delay before reading each sector - card_manager handles retries
            self._log.debug({
                'action': 'reading_sector',
                'sector': sector
            })
            
            # Try multiple times to read each sector
            max_sector_attempts = 3  # Increased from 2 to 3
            sector_data = None
            
            for attempt in range(1, max_sector_attempts + 1):
                read_start = time.time()
                trailer, blocks = _RealReader.get_blocks(sector)
                id, sector_data = self.read_sector(trailer=trailer, blocks=blocks)
                read_duration = time.time() - read_start
                
                if id is not None and sector_data is not None:
                    self._log.debug({
                        'action': 'sector_read_success',
                        'sector': sector,
                        'attempt': attempt,
                        'duration': read_duration
                    })
                    break
                    
                if attempt < max_sector_attempts:
                    self._log.warning({
                        'action': 'retrying sector read',
                        'sector': sector,
                        'attempt': attempt,
                        'duration': read_duration
                    })
                    # No need for delay between sector read retries - card_manager handles retries
            
            if id is None:  # The card was removed or read failed
                self._log.debug({
                    'action': 'read card body failed',
                    'sector': sector,
                    'original_id': original_id
                })
                
                # If we have the original ID but the sector read failed, we can still return
                # a partial body with what we've read so far
                if original_id is not None and body:
                    self._log.warning({
                        'action': 'partial_body_read_with_original_id',
                        'original_id': original_id,
                        'body_length': len(body),
                        'sectors_read': sector - gwent.messaging.card.Message.body_sector_start()
                    })
                    return original_id, body
                
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
            
            # No need for delay after reading each sector - card_manager handles retries

        self.log_time('read card body', body_start)
        
        self._log.debug({
            'action': 'completed card body read',
            'body_length': len(body),
            'n_bytes': n_bytes,
            'duration': time.time() - body_start,
            'id': id,
            'original_id': original_id
        })

        # If we have no ID but we have the original ID, use that
        if id is None and original_id is not None and body:
            self._log.warning({
                'action': 'using_original_id_for_completed_body',
                'original_id': original_id,
                'body_length': len(body)
            })
            id = original_id

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


class RealWriter(_BaseWriter, _RealReader):
    def __init__(self):
        super().__init__()
        self._log.info({'action': 'startup_reset'})
        self.reset()

    def reset(self):
        """Reset the RFID reader to ensure it's in a clean state"""
        self._log.info({
            'action': 'resetting_rfid_reader',
            'timestamp': time.time()
        })

        with gwent.hal.spi_lock:
            try:
                self._setup_rfid()

                id, _ = self._rfid.read_id(attempts=1)
                if id is not None:
                    self._log.debug({
                        'action': 'rfid_reader_reset_complete_with_card_present',
                        'id': id,
                    })
                else:
                    self._log.debug({
                        'action': 'rfid_reader_reset_complete_no_card_detected',
                    })

                return True
            except Exception as e:
                self._log.error({
                    'action': 'rfid_reader_reset_failed',
                    'error': str(e),
                    'error_traceback': traceback.format_exc(),
                })
                return False
    
    def write_card_impl(self, card: gwent.messaging.card.Message) -> int:
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
        debug_enabled = self._log.isEnabledFor(DEBUG)

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
        if self._log.isEnabledFor(DEBUG):
            self._log.debug({
                'action': 'string written',
                'id': id,
                'len(text)': len(text),
                'text': text,
                'len(total_written)': len(written),
                'total_written': written,
            })
        return id, written
