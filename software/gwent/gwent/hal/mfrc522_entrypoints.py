import logging
import time

import gwent.hal.rfid
import gwent.log


def mfrc522_read_all_sectors():
    gwent.log.setup(level='debug')
    log = logging.getLogger(__name__)
    mfrc522 = gwent.hal.rfid.Reader()

    sectors = gwent.hal.rfid.ALL_SECTORS
    start = time.time()
    log.info(f'Reading sectors {sectors}, start={start}')
    for sector in sectors:
        trailer, blocks = gwent.hal.rfid.get_blocks(sector)
        if log.isEnabledFor(logging.DEBUG):
            log.debug(
                f'Reading sector={sector}, trailer={trailer}, blocks={blocks}')
        id, text = mfrc522.read(block=True, trailer=trailer, blocks=blocks)
        if log.isEnabledFor(logging.DEBUG):
            logging.debug(f"id={id}, text='{text}'")
    end = time.time()
    log.info(f'elapsed={end - start}, start={start}, end={end}')


def mfrc522_write_all_sectors():
    gwent.log.setup(level='debug')
    log = logging.getLogger(__name__)
    mfrc522 = gwent.hal.rfid.Writer()

    sectors = gwent.hal.rfid.ALL_SECTORS
    start = time.time()
    log.info(f'Writing sectors {sectors}, start={start}')
    for sector in sectors:
        trailer, blocks = gwent.hal.rfid.get_blocks(sector)
        text = f"this is sector {sector}"
        if log.isEnabledFor(logging.DEBUG):
            log.debug(f"Writing text='{text}', sector={sector}, "
                      f"trailer={trailer}, blocks={blocks}")
        id, text = mfrc522.write_sector(text, block=False,
                                        trailer=trailer, blocks=blocks)
        if log.isEnabledFor(logging.DEBUG):
            logging.debug(f"Wrote sector={sector}, id={id}, text='{text}'")
    end = time.time()
    log.info(f'elapsed={end - start}, start={start}, end={end}')


if __name__ == '__main__':
    mfrc522_write_all_sectors()
