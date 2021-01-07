#!/usr/local/bin/python
import board
import busio
import digitalio
import logging
from flask import Flask

import adafruit_rfm69


class LoRa:
    '''
    This class handles communication to the sensor pi
    The channel is encrypted to prevent interference from other LoRa devices,
    It does not serve a security purpose, hence the weak encryption key
    '''
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
        '''
        Initializes the SPI channel and the RMF69 python API
        '''
        spi = busio.SPI(self.__PINS['sck'],
                        MOSI=self.__PINS['mosi'],
                        MISO=self.__PINS['miso'])
        cs = digitalio.DigitalInOut(self.__PINS['cs'])
        rst = digitalio.DigitalInOut(self.__PINS['rst'])
        self.lora = adafruit_rfm69.RFM69(spi, cs, rst, self.__SIGNAL_FREQUENCY)
        self.lora.encryption_key = self.__ENCRYPTION_KEY
        logging.debug(
            f'Init\'d LoRa board with freq: {self.lora.frequency_mhz}'
            f', bitrate: {self.lora.bitrate / 1000} kbit/s, f. deviation: '
            f'{self.lora.frequency_deviation/1000} khz, and encryption key: '
            f'{self.lora.encryption_key}')

    def receive_message(self):
        '''
        Waits for a message with a 2 second timeout
        '''
        logging.debug('Waiting for message...')
        packets = self.lora.receive(timeout=self.__PACKET_WAIT)
        if packets:
            logging.debug(f'Got packets: {packets}')
            return packets
        return False

    def send_message(self, message: any):
        '''
        Sends a message
        '''
        logging.debug(f'Sending message: {message}')
        packets = bytes(message, 'utf-8')
        self.lora.send(packets)

    def send_and_wait(self, message):
        '''
        Sends a message, waits for a responce,
        and retries up to 4 times if no reply is detected
        '''
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


class Master:
    '''
    Main class for sending LoRa commands and parsing responces
    '''

    def __init__(self):
        '''
        Init the LoRa class and send a ping to check
        Sensor Pi status
        '''
        self.com = LoRa()
        logging.info('Pining slave')
        rsp = self.com.send_and_wait('ping|')
        print(f'Satellite is {rsp}')

    def get_temp(self):
        temp = self.com.send_and_wait('iot_g_temp|')
        logging.info(f'Got temp from satellite: {temp}ºC')
        if temp:
            return float("{:.1f}".format(float(temp.decode())))
        return 0

    def get_hmdt(self):
        hmdt = self.com.send_and_wait('iot_g_hmdt|')
        logging.info(f'Got hmdt from satellite: {hmdt}')
        if hmdt:
            return int(hmdt.decode())
        return 0

    def run_pump(self, volume):
        status = self.com.send_and_wait(f'iot_pmp_ctrl|{str(volume)}')
        logging.info(status)
        return status.decode()


if __name__ == "__main__":
    logging.root.setLevel(logging.DEBUG)
    master = Master()  # init the master class

    node = Flask(__name__)  # inint the Flask app

    prev_temp = master.get_temp()  # Get initial readings
    prev_hmdt = master.get_hmdt()

    @node.route("/")
    def root():  # Return a generic message if the server is alive
        return "IoT-ICL DE Weather Master Node running..."

    @node.route("/hmdt")
    def humidity():  # return the measured humidity
        global prev_hmdt
        humidity = master.get_hmdt()
        if humidity:
            prev_hmdt = humidity
            return {'success': True, 'value': humidity}
        # If humidity could not be measured, return the previous value
        return {'success': False, 'value': prev_hmdt}

    @node.route("/temp")
    def temp():  # return the measured temperature
        global prev_temp
        temp = master.get_temp()
        if temp:
            prev_temp = temp
            return {'success': True, 'value': temp}
        # If temperature could not be measured, return the previous value
        return {'success': False, 'value': prev_temp}

    # Start the server
    node.run(host='0.0.0.0', port='3333', use_reloader=False)
