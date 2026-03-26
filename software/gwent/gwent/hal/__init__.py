import threading

# Shared SPI bus lock — RFID (CE0) and OLED (CE1) share the SPI bus
# and must not access it concurrently from different threads.
# RLock allows reentrant acquisition (e.g. redraw -> clear -> println).
spi_lock = threading.RLock()
