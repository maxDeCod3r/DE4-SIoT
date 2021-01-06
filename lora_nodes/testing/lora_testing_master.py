import board
import busio
import digitalio

import adafruit_rfm69

SIGNAL_FREQUENCY = 915.0
ENCRYPTION_KEY = b"\x01\x01\x01\x01\x01\x01\x01\x01\x02\x02\x02\x02\x02\x02\x02\x02"

pins = {
    'miso': board.MISO,
    'mosi': board.MOSI,
    'sck': board.SCK,
    'cs': board.D22,
    'rst': board.D27
}

spi = busio.SPI(pins['sck'], MOSI=pins['mosi'], MISO=pins['miso'])
cs = digitalio.DigitalInOut(pins['cs'])
reset = digitalio.DigitalInOut(pins['rst'])

lora = adafruit_rfm69.RFM69(spi, cs, reset, SIGNAL_FREQUENCY)
lora.encryption_key = (ENCRYPTION_KEY)

while True:
    packet = lora.receive(timeout=2)
    if packet:
        print(f"Recieved data: {packet}")
        print(f"RSSI: {lora.rssi}")
