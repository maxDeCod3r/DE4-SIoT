#!/usr/local/bin/python
from firebase_admin import credentials, firestore, initialize_app
from requests import get as api_get
from time import time as timestamp
from time import sleep as wait
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)


class EmailSender:
    def __init__(self):
        pass


class DataCollector:
    __CERT_PATH = "secrets/icl-iot-weather-firebase-adminsdk.json"
    __API_KEY_PATH = "secrets/weather_api_key.txt"
    __CITY = "London"
    __API_ENDPOINT = "api.openweathermap.org/data/2.5/weather"
    __NODE_T_ENDPOINT = "http://ss.maxhunt.design:3333/temp"
    __NODE_H_ENDPOINT = "http://ss.maxhunt.design:3333/hmdt"
    __TESTING = False

    def __init__(self):
        self.init_firebase()
        self.init_api()

    def init_firebase(self):
        cred = credentials.Certificate(self.__CERT_PATH)
        initialize_app(cred)
        self.firestore_db = firestore.client()

    def init_api(self):
        with open(self.__API_KEY_PATH, "r") as api_key_file:
            self.api_key = api_key_file.read()

        self.request_url = (f"https://{self.__API_ENDPOINT}?"
                            f"q={self.__CITY} &"
                            f"appid={str(self.api_key)}".split('\n')[0])

    def get_weather_data(self):
        api_rsp = api_get(self.request_url)
        return api_rsp

    def process_api_data(self, api_rsp):
        api_data = api_rsp
        if api_data.status_code != 200:
            logging.warning("Big fuckup, "
                            f"expected 200 but got {api_data.status_code}")
            logging.warning(f"Response: {api_data.text}")
            # Email me with this data
            # generate obvious outlier data and stil push
            # or push previous data
            return {"data": "TODO"}

        try:
            rsp = api_get(self.__NODE_H_ENDPOINT)
            rsp_json = rsp.json()
            local_hmdt = rsp_json.get('value', False)
        except Exception as e:
            logging.error(f'Failed to get data from humidity node!!!, {e}')
            local_hmdt = -50

        try:
            rsp = api_get(self.__NODE_T_ENDPOINT)
            rsp_json = rsp.json()
            local_temp = rsp_json.get('value', False)
        except Exception as e:
            logging.error(f'Failed to get data from local temp node!!!, {e}')
            local_temp = -50

        weather_data = api_data.json()
        station_data = weather_data.get('main', False)
        if station_data:
            current_temp_kelvin = station_data.get('temp', {})
            current_temp_celcius = current_temp_kelvin - 273.15
            current_humidity_pct = station_data.get('humidity', 0)
            cloud_data = weather_data.get('clouds', {})
            current_cloud_pct = cloud_data.get('all', 0)
            wind_data = weather_data.get('wind', {})
            current_wind_ms = wind_data.get('speed', 0)
            rain_data = weather_data.get('rain', {})
            rain_mm_1h = rain_data.get('1h', 0)

            relevant_data = {
                "timestamp": timestamp(),
                "datetime": datetime.now(),
                "temp": current_temp_celcius,
                "humidity": current_humidity_pct,
                "cloud": current_cloud_pct,
                "wind": current_wind_ms,
                "rain_1h": rain_mm_1h,
                "local_soil_humidity": local_hmdt,
                "local_soil_temperature": local_temp,
                "is_test": self.__TESTING
            }
            return relevant_data
        else:
            logging.warning("COULD NOT GET STATION DATA")
            relevant_data = {
                "timestamp": timestamp(),
                "datetime": datetime.now()
            }
            return relevant_data

    def upload_to_firebase(self, data):
        try:
            self.firestore_db.collection(u'weather_data').add(data)
        except Exception as e:
            logging.warning(f"FAILED TO UPLOAD TO FIREBASE: {e}")
            # Email me

    def collect_data(self):
        try:
            logging.info(f"Running collection at {datetime.now()}")
            weather_data = self.get_weather_data()
            processed_data = self.process_api_data(weather_data)
            self.upload_to_firebase(processed_data)
        except Exception as e:
            logging.warning(f"ERROR: {e}")
            # Email me

    def run_time_loop(self):
        while True:
            self.collect_data()
            wait(60*60*1)  # wait 1h
            # wait(10*1*1)  # wait 1h


if __name__ == "__main__":
    weather_logger = DataCollector()
    weather_logger.run_time_loop()
