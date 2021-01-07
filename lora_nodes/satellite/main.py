#!/usr/local/bin/python
import board
import busio
import digitalio
import time
import logging

import adafruit_rfm69
from adafruit_seesaw.seesaw import Seesaw


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
        logging.debuddg(
            f'Init\'d LoRa board with freq: {self.lora.frequency_mhz}, '
            f'bitrate: {self.lora.bitrate / 1000} kbit/s, f. deviation: '
            f'{self.lora.frequency_deviation/1000} khz, and encryption key: '
            f'{self.lora.encryption_key}')

    def receive_message(self):
        '''
        Waits for a message with a 2 second timeout
        '''
        packets = self.lora.receive(timeout=self.__PACKET_WAIT)
        if packets:
            logging.debug(f'Got packets: {packets}')
            return packets
        return False

    def send_message(self, message):
        '''
        Sends a message
        '''
        logging.debug(f'Sending message: {message}')
        packets = bytes(message, 'utf-8')
        self.lora.send(packets)


class WateringPump:
    '''
    This class is responsible for running the water pump
    '''
    __PINS = {'pwm': board.D20}
    __FLOW_RATE = 130

    def __init__(self):
        '''
        Initializes the DigitalIO pin controlling the pump
        '''
        self.ctrl_pin = self.__PINS['pwm']
        self.pump = digitalio.DigitalInOut(self.ctrl_pin)
        self.pump.direction = digitalio.Direction.OUTPUT
        self.pump.value = False
        logging.debug(f'Init\'d pump at pin {self.ctrl_pin}, '
                      f'Power state is {self.pump.value}')

    def dispense(self, volume: int):
        '''
        Pump flow rate is 130 ml/min at 5V
        need to convert vol in ml to time duration in s
        target_vol*60/130 = pump dispensing duration in seconds
        '''
        flow_rate = self.__FLOW_RATE
        run_duration_seconds = volume*60/flow_rate
        self.__run_for(run_duration_seconds)

    def __run_for(self, duration: float):
        '''
        Runs the pump for n seconds
        '''
        start_time = time.time()
        end_time = start_time + duration
        self.pump.value = True
        logging.info('Starting pump')
        while time.time() < end_time:
            pass
        self.pump.value = False
        logging.info('Stopping pump')


class SoliSensor:
    '''
    This class controls the i2c soul and humidity sensor
    '''
    __PINS = {
        'sda': board.SDA,
        'scl': board.SCL
    }

    def __init__(self):
        '''
        Initializes the i2c channel and the python Seesaw API
        '''
        i2c = busio.I2C(self.__PINS['scl'], self.__PINS['sda'])
        self.sensor = Seesaw(i2c, addr=0x36)
        logging.debug(
            f'Init\'d soil sensor, humidity: {self.sensor.moisture_read()}, '
            f'temp: {self.sensor.get_temp()}')

    def get_temp(self):
        '''
        Reads the soil sensor temperature
        '''
        try:
            temp = self.sensor.get_temp()
            logging.debug(f'Temp: {temp}')
            return temp
        except Exception as e:
            logging.error(f'Could not get temp!, {e}')
            return -50  # return obvously wrong data

    def get_hmdt(self):
        '''
        Reads the soil sensor humidity
        '''
        try:
            hmdt = self.sensor.moisture_read()
            logging.debug(f'Humidity: {hmdt}')
            return hmdt
        except Exception as e:
            logging.error(f'Could not get hmdt!, {e}')
            return -50  # return obvously wrong data


class SensorNode:
    '''
    Main class for executing commands and returning
    measured data
    '''

    def __init__(self):
        '''
        Initializes the LoRa class and the sensors and pump
        '''
        self.com = LoRa()
        self.probe = SoliSensor()
        self.pump = WateringPump()

    def wait_for_instructions(self):
        '''
        Waits for and executes instructions

        Instructions:
            ping: check that node is alive
            iot_g_temp: get sensor temperature
            iot_g_hmdt: get sendor humidity
            iot_pmp_ctrl: run the pump
        '''
        self.__instrucitons = {
            'ping': self.ping,
            'iot_g_temp': self.get_soil_temp,
            'iot_g_hmdt': self.get_soil_hmdt,
            'iot_pmp_ctrl': self.pump_control
        }
        while True:  # Do this forever
            command = self.com.receive_message()
            if command:
                command = command.decode()
                logging.debug(f'Decoded command: {command}')
                commands = str(command).split('|')
                logging.debug(f'Processed commands: {commands}')
                try:
                    self.__instrucitons[commands[0]](commands[1])
                except Exception as e:
                    logging.error(f'Exception: {e}')

    def ping(self, *_):
        time.sleep(0.5)
        # The dalay is necessary as otherwise the Pi may send a response
        #  before the master Pi has started lsitening
        self.com.send_message('OK')

    def get_soil_temp(self, *_):
        soil_temp = self.probe.get_temp()
        time.sleep(0.5)
        self.com.send_message(str(soil_temp))

    def get_soil_hmdt(self, *_):
        soil_hmdt = self.probe.get_hmdt()
        time.sleep(0.5)
        self.com.send_message(str(soil_hmdt))

    def pump_control(self, volume):
        water_qty = int(volume)
        logging.info(f'Dispensing {water_qty} ml.')
        time.sleep(0.5)
        self.com.send_message('OK')
        self.pump.dispense(water_qty)


if __name__ == "__main__":
    logging.root.setLevel(logging.DEBUG)
    sensor_node = SensorNode()  # init the SensorNode class, and children
    sensor_node.wait_for_instructions()  # wait for instructions forever
