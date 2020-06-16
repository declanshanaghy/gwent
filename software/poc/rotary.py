#!/usr/bin/env python3

import time
import gaugette.gpio
import gaugette.rotary_encoder
import gaugette.switch

# https://learn.adafruit.com/pro-trinket-rotary-encoder/example-rotary-encoder-volume-control

# Pin numbers are Wiring pin numbers.
# They differ from hardware pin or GPIO ids.
# Connect your C pin of the encoder to Ground.
A_PIN = 1
B_PIN = 0
SW_PIN = 2

gpio = gaugette.gpio.GPIO()
encoder = gaugette.rotary_encoder.RotaryEncoder(gpio, A_PIN, B_PIN)
encoder.start()

sw = gaugette.switch.Switch(gpio, SW_PIN)
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
