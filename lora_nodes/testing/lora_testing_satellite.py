import board
import busio
import digitalio
import time

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
    print("Temperature: {0}C".format(lora.temperature))
    print("Frequency: {0}mhz".format(lora.frequency_mhz))
    print("Bit rate: {0}kbit/s".format(lora.bitrate / 1000))
    print("Frequency deviation: {0}hz".format(lora.frequency_deviation))

    str_time = str(time.time())
    msg = f"Testing message {str_time}"
    lora.send(bytes(msg, 'utf-8'))
    print(f'Sent message: {msg}')
    time.sleep(2)
