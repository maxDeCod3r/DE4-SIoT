#!/usr/local/bin/python
import logging
import time

import adafruit_rfm69
import board
import busio
import digitalio
from requests import get as api_get


class LoRa:
    __SIGNAL_FREQUENCY = 915.0
    __ENCRYPTION_KEY = b"\x01\x01\x01\x01\x01\x01\x01\x01\x02\x02\x02\x02\x02\x02\x02\x02"
    __PINS = {
        'miso': board.MISO,
        'mosi': board.MOSI,
        'sck': board.SCK,
        'cs': board.D22,
        'rst': board.D27
    }
    __PACKET_WAIT = 2
    __MAX_ATTEMPTS = 5

    def __init__(self):
        spi = busio.SPI(self.__PINS['sck'],
                        MOSI=self.__PINS['mosi'],
                        MISO=self.__PINS['miso'])
        cs = digitalio.DigitalInOut(self.__PINS['cs'])
        rst = digitalio.DigitalInOut(self.__PINS['rst'])
        self.lora = adafruit_rfm69.RFM69(spi, cs, rst, self.__SIGNAL_FREQUENCY)
        self.lora.encryption_key = self.__ENCRYPTION_KEY
        logging.debug(f'Init\'d LoRa board with freq: {self.lora.frequency_mhz}, bitrate: {self.lora.bitrate / 1000} kbit/s, f. deviation: {self.lora.frequency_deviation/1000} khz, and encryption key: {self.lora.encryption_key}')

    def receive_message(self):
        logging.debug('Waiting for message...')
        packets = self.lora.receive(timeout=self.__PACKET_WAIT)
        if packets:
            logging.debug(f'Got packets: {packets}')
            return packets
        return False

    def send_message(self, message):
        logging.debug(f'Sending message: {message}')
        packets = bytes(message, 'utf-8')
        self.lora.send(packets)

    def send_and_wait(self, message):
        attempt = 0
        max_attempts = self.__MAX_ATTEMPTS
        waiting_for_response = True
        response = None

        while waiting_for_response:
            logging.debug(f'Attempt {attempt}...')
            attempt += 1

            self.send_message(message)
            response = self.receive_message()

            if attempt > max_attempts or response:
                waiting_for_response = False

        return response


class Irrigator:
    __DATA_ENDPOINT = "http://api.maxhunt.design/water"

    def __init__(self):
        self.com = LoRa()
        self.yesterday_water = 0

    def get_today_watering_vol(self):
        endpoint = self.__DATA_ENDPOINT
        rsp = api_get(endpoint)
        if rsp.status_code != 200:
            logging.error(f'Got code {rsp.status_code} from server, using yesterday\'s value')
            return self.yesterday_water
        today_water = int(rsp.json().get('value'))
        self.yesterday_water = today_water
        return today_water

    def send_watering_command(self, volume: int):
        self.com.send_and_wait(f'iot_pmp_ctrl|{str(volume)}')

    def mainloop(self):
        while True:
            watering_vol = self.get_today_watering_vol()
            self.send_watering_command(watering_vol)
            time.sleep(60*60*24)


if __name__ == "__main__":
    irrigator = Irrigator()
    irrigator.mainloop()
