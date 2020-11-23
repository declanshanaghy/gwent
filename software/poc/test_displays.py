    #!/usr/bin/env python

import time

import qwiic_tca9548a
import board
import busio
import adafruit_is31fl3731
import adafruit_framebuf


def doit(displays):
    for display in displays:
        print("Display is %s", display)
        mux.disable_all()
        mux.enable_channels(display[0])

        mux.list_channels()

        matrix = display[1]
        draw_border(matrix)
        draw_text(matrix, "hello")

        time.sleep(1)

        clear(matrix)


def clear(matrix):
    matrix.fade(fade_in=500, fade_out=500, pause=1000)

    # draw a box on the matrix
    # first draw the top and bottom edges
    for x in range(matrix.width):
        for y in range(matrix.height):
            matrix.pixel(x, y, 0)


def draw_border(matrix):
    matrix.fade(fade_in=500, fade_out=500, pause=1000)

    # draw a box on the matrix
    # first draw the top and bottom edges
    for x in range(matrix.width):
        matrix.pixel(x, 0, 255)
        matrix.pixel(x, matrix.height - 1, 255)
    # now draw the left and right edges
    for y in range(matrix.height):
        matrix.pixel(0, y, 255)
        matrix.pixel(matrix.width - 1, y, 255)


def draw_text(display, text_to_show):
    # Create a framebuffer for our display
    buf = bytearray(32)  # 2 bytes tall x 16 wide = 32 bytes (9 bits is 2 bytes)
    fb = adafruit_framebuf.FrameBuffer(
        buf, display.width, display.height, adafruit_framebuf.MVLSB
    )

    frame = 0  # start with frame 0
    for i in range(len(text_to_show) * 9):
        fb.fill(0)
        fb.text(text_to_show, -i + display.width, 0, color=1)

    # to improve the display flicker we can use two frame
    # fill the next frame with scrolling text, then
    # show it.
    display.frame(frame, show=False)
    # turn all LEDs off
    display.fill(0)
    for x in range(display.width):
        # using the FrameBuffer text result
        bite = buf[x]
        for y in range(display.height):
            bit = 1 << y & bite
            # if bit > 0 then set the pixel brightness
            if bit:
                display.pixel(x, y, 50)

        # now that the frame is filled, show it.
        display.frame(frame, show=True)
        frame = 0 if frame else 1


# Initialize Mux and i2C bus
mux = qwiic_tca9548a.QwiicTCA9548A(address=0x70)
print("mux connected ", mux.is_connected())

i2c = busio.I2C(board.SCL, board.SDA)

displays = []
channels = [0, 7]
for ch in channels:
    mux.enable_channels(ch)
    displays.append((ch, adafruit_is31fl3731.Matrix(i2c, address=0x74)))
    mux.disable_all()

doit(displays)
