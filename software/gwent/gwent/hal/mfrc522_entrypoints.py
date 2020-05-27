import logging
import time

import gwent.hal.rfid
import gwent.log


def mfrc522_read_all_sectors():
    # import pydevd_pycharm
    # pydevd_pycharm.settrace('192.168.1.143', port=31337,
    #                         stdoutToServer=True, stderrToServer=True)

    gwent.log.setup(level='debug')
    log = logging.getLogger(__name__)
    mfrc522 = gwent.hal.rfid.Reader()

    sectors = gwent.hal.rfid.ALL_SECTORS
    start = time.time()
    log.info(f'Reading sectors {sectors}, start={start}')
    for sector in sectors:
        trailer, blocks = gwent.hal.rfid.Reader.get_blocks(sector)
        if log.isEnabledFor(logging.DEBUG):
            log.debug(
                f'Reading sector={sector}, trailer={trailer}, blocks={blocks}')
        id, text, tries = mfrc522.read_sector(block=True, trailer=trailer,
                                              blocks=blocks)
        if log.isEnabledFor(logging.DEBUG):
            logging.debug(f"Read id={id}, sector={sector}, "
                          f"tries={tries}, text='{text}'")
    end = time.time()
    log.info(f'elapsed={end - start}, start={start}, end={end}')


def mfrc522_write_all_sectors():
    # import pydevd_pycharm
    # pydevd_pycharm.settrace('192.168.1.143', port=31337,
    #                         stdoutToServer=True, stderrToServer=True)

    gwent.log.setup(level='debug')
    log = logging.getLogger(__name__)
    mfrc522 = gwent.hal.rfid.Writer()

    sectors = gwent.hal.rfid.ALL_SECTORS
    start = time.time()
    log.info(f'Writing sectors {sectors}, start={start}')
    for sector in sectors:
        trailer, blocks = gwent.hal.rfid.Reader.get_blocks(sector)
        text = f"this is sector {sector}"
        if log.isEnabledFor(logging.DEBUG):
            log.debug(f"Writing sector={sector}, trailer={trailer}, "
                      f"blocks={blocks}, text='{text}'")
        id, text, tries = mfrc522.write_sector(text, block=True,
                                               trailer=trailer, blocks=blocks)
        if log.isEnabledFor(logging.DEBUG):
            logging.debug(f"Wrote id={id}, sector={sector}, "
                          f"tries={tries}, text='{text}'")
    end = time.time()
    log.info(f'elapsed={end - start}, start={start}, end={end}')


if __name__ == '__main__':
    mfrc522_write_all_sectors()
