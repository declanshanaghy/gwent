#!/usr/bin/env python3

import time
from gwent.hal.rotary_gpio import DirectGPIORotaryEncoder, DirectGPIOSwitch

# https://learn.adafruit.com/pro-trinket-rotary-encoder/example-rotary-encoder-volume-control

# BCM pin numbers (not Wiring pin numbers)
A_PIN = 23  # GPIO23
B_PIN = 24  # GPIO24
SW_PIN = 25  # GPIO25

encoder = DirectGPIORotaryEncoder(A_PIN, B_PIN)
encoder.start()

sw = DirectGPIOSwitch(SW_PIN)
last_state = sw.get_state()

counter = 0

while True:
    delta = encoder.get_cycles()
    if delta != 0:
        counter += delta
        print("count is %d" % counter)
    else:
        time.sleep(0.1)

    state = sw.get_state()
    if state != last_state:
        print("switch %d" % state)
        last_state = state
