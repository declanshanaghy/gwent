#!/usr/bin/env python3
"""
Low-level RFID-RC522 hardware diagnostic.
Checks SPI communication, chip version, antenna, and card detection.
"""

import sys
import time
import spidev
import RPi.GPIO as GPIO

# MFRC522 registers
CommandReg    = 0x01
Status1Reg    = 0x07
Status2Reg    = 0x08
FIFOLevelReg  = 0x0A
ControlReg    = 0x0C
BitFramingReg = 0x0D
TxControlReg  = 0x14
TxAutoReg     = 0x15
TModeReg      = 0x2A
TPrescalerReg = 0x2B
TReloadRegH   = 0x2C
TReloadRegL   = 0x2D
VersionReg    = 0x37
AutoTestReg   = 0x36

# Commands
PCD_IDLE       = 0x00
PCD_RESETPHASE = 0x0F
PCD_TRANSCEIVE = 0x0C

# Card commands
PICC_REQIDL = 0x26
PICC_REQALL = 0x52

# SPI config
SPI_BUS    = 0
SPI_DEVICE = 0
SPI_SPEED  = 1000000

# GPIO
RST_PIN = 22  # Physical pin 22 = GPIO25 in BCM... but BOARD mode uses 22

KNOWN_VERSIONS = {
    0x88: "MFRC522 clone (Fudan FM17522)",
    0x90: "MFRC522 v0.0",
    0x91: "MFRC522 v1.0",
    0x92: "MFRC522 v2.0",
    0xB2: "FM17522E",
}


def read_reg(spi, addr):
    return spi.xfer2([((addr << 1) & 0x7E) | 0x80, 0])[1]


def write_reg(spi, addr, val):
    spi.xfer2([(addr << 1) & 0x7E, val])


def set_bit_mask(spi, reg, mask):
    val = read_reg(spi, reg)
    write_reg(spi, reg, val | mask)


def clear_bit_mask(spi, reg, mask):
    val = read_reg(spi, reg)
    write_reg(spi, reg, val & (~mask))


def reset_chip(spi):
    write_reg(spi, CommandReg, PCD_RESETPHASE)
    time.sleep(0.05)


def init_chip(spi):
    """Minimal MFRC522 init sequence."""
    reset_chip(spi)
    write_reg(spi, TModeReg, 0x8D)
    write_reg(spi, TPrescalerReg, 0x3E)
    write_reg(spi, TReloadRegH, 0x00)
    write_reg(spi, TReloadRegL, 0x1E)  # ~25ms timeout
    write_reg(spi, TxAutoReg, 0x40)
    write_reg(spi, 0x11, 0x3D)  # ModeReg: CRC preset 6363h


def antenna_on(spi):
    val = read_reg(spi, TxControlReg)
    if not (val & 0x03):
        set_bit_mask(spi, TxControlReg, 0x03)


def request_card(spi):
    """Send REQA command, return (status, bits) tuple."""
    write_reg(spi, BitFramingReg, 0x07)  # 7 bits for short frame

    # Flush FIFO
    set_bit_mask(spi, 0x0A, 0x80)  # FlushBuffer

    # Write REQA to FIFO
    write_reg(spi, 0x09, PICC_REQALL)  # FIFODataReg

    # Execute transceive
    write_reg(spi, CommandReg, PCD_TRANSCEIVE)
    set_bit_mask(spi, BitFramingReg, 0x80)  # StartSend

    # Wait for completion
    timeout = 50
    for _ in range(timeout):
        irq = read_reg(spi, 0x04)  # CommIrqReg
        if irq & 0x30:  # RxIRq or IdleIRq
            break
        time.sleep(0.001)

    # Check error
    err = read_reg(spi, 0x06)  # ErrorReg
    fifo_level = read_reg(spi, FIFOLevelReg)

    write_reg(spi, CommandReg, PCD_IDLE)

    if fifo_level >= 2 and not (err & 0x1B):
        atqa_lo = read_reg(spi, 0x09)
        atqa_hi = read_reg(spi, 0x09)
        return True, (atqa_hi << 8) | atqa_lo
    return False, 0


def p(ok, msg):
    status = "OK" if ok else "FAIL"
    print(f"  [{status:>4}] {msg}")
    return ok


def main():
    print("RFID-RC522 Hardware Diagnostic")
    print("=" * 40)
    all_ok = True

    # --- GPIO setup ---
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BOARD)
    GPIO.setup(RST_PIN, GPIO.OUT)
    GPIO.output(RST_PIN, 1)
    time.sleep(0.05)

    # --- SPI ---
    print("\n1. SPI Bus")
    try:
        spi = spidev.SpiDev()
        spi.open(SPI_BUS, SPI_DEVICE)
        spi.max_speed_hz = SPI_SPEED
        p(True, f"SPI{SPI_BUS}.{SPI_DEVICE} opened at {SPI_SPEED}Hz")
    except Exception as e:
        p(False, f"SPI open failed: {e}")
        GPIO.cleanup()
        return 1

    # --- Chip version ---
    print("\n2. Chip Version")
    version = read_reg(spi, VersionReg)
    chip_name = KNOWN_VERSIONS.get(version, "UNKNOWN")
    ok = version in KNOWN_VERSIONS
    all_ok &= p(ok, f"Version register: 0x{version:02X} ({chip_name})")
    if not ok:
        p(False, "Cannot communicate with MFRC522. Check wiring:")
        print("         RC522 SDA  -> Pin 24 (GPIO8/CE0)")
        print("         RC522 SCK  -> Pin 23 (GPIO11/SCLK)")
        print("         RC522 MOSI -> Pin 19 (GPIO10/MOSI)")
        print("         RC522 MISO -> Pin 21 (GPIO9/MISO)")
        print("         RC522 RST  -> Pin 22 (GPIO25)")
        print("         RC522 3.3V -> Pin 1 or 17")
        print("         RC522 GND  -> Pin 6, 9, 14, 20, 25, 30, 34, or 39")
        spi.close()
        GPIO.cleanup()
        return 1

    # --- Init & register sanity ---
    print("\n3. Register Access")
    init_chip(spi)
    tmode = read_reg(spi, TModeReg)
    p(True, f"TModeReg: 0x{tmode:02X}")

    status1 = read_reg(spi, Status1Reg)
    all_ok &= p(True, f"Status1Reg: 0x{status1:02X}")

    status2 = read_reg(spi, Status2Reg)
    p(True, f"Status2Reg: 0x{status2:02X}")

    # --- Antenna ---
    print("\n4. Antenna")
    antenna_on(spi)
    tx_ctrl = read_reg(spi, TxControlReg)
    ant_on = bool(tx_ctrl & 0x03)
    all_ok &= p(ant_on, f"TxControlReg: 0x{tx_ctrl:02X} (antenna {'ON' if ant_on else 'OFF'})")

    # --- Card scan using SimpleMFRC522 ---
    print("\n5. Card Scan (3 second window)")
    print("   Place a card on the reader now...")
    spi.close()
    GPIO.cleanup()

    GPIO.setwarnings(False)
    import mfrc522
    reader = mfrc522.SimpleMFRC522(pin_mode=GPIO.BCM)
    found = False
    start = time.time()
    while time.time() - start < 3.0:
        card_id, status = reader.read_id(attempts=1)
        if card_id:
            found = True
            p(True, f"Card detected! ID: {card_id}")
            # Try to read data
            rid, text, raw = reader.read(trailer=11, blocks=[8, 9, 10], attempts=3)
            if text and text.strip():
                p(True, f"Card data: {text.strip()[:80]}")
            else:
                p(True, "Card has no data (blank)")
            break
        time.sleep(0.05)

    if not found:
        p(False, "No card detected (this is OK if no card was present)")

    GPIO.cleanup()

    # --- Summary ---
    print("\n" + "=" * 40)
    if all_ok:
        print("RFID hardware is responding correctly.")
    else:
        print("Some checks failed. Review output above.")

    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
