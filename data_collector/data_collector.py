#!/usr/local/bin/python
from firebase_admin import credentials, firestore, initialize_app
from requests import get as api_get
from time import time as timestamp
from time import sleep as wait
from datetime import datetime
import logging


class DataCollector:
    '''
    This large class is responsible for api queries,
    and uploading the recieved data to a firebase firestore instance.
    You may need to change the below constants for proper functionality.
    '''

    # Defining constants
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
        '''
        Loading the API credentials and initializing the instance
        '''
        cred = credentials.Certificate(self.__CERT_PATH)
        initialize_app(cred)
        self.firestore_db = firestore.client()

    def init_api(self):
        '''
        Loading the API key and defining the endpoint URL
        '''
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
        if api_data.status_code != 200:  # checking the stattus code
            logging.error("Big problem, "
                          f"expected 200 but got {api_data.status_code}")
            logging.error(f"Response: {api_data.text}")
            return {"data": None}

        try:  # Try to get the local sensor data
            rsp = api_get(self.__NODE_H_ENDPOINT)
            rsp_json = rsp.json()
            local_hmdt = rsp_json.get('value', False)
        except Exception as e:
            logging.error(f'Failed to get data from humidity node!!!, {e}')
            local_hmdt = -50  # Make it an obviously false value

        try:  # Try to get the local sensor data
            rsp = api_get(self.__NODE_T_ENDPOINT)
            rsp_json = rsp.json()
            local_temp = rsp_json.get('value', False)
        except Exception as e:
            logging.error(f'Failed to get data from local temp node!!!, {e}')
            local_temp = -50  # Make it an obviously false value

        weather_data = api_data.json()
        station_data = weather_data.get('main', False)
        if station_data:  # Parse the data if it exists
            current_temp_kelvin = station_data.get('temp', {})
            current_temp_celcius = current_temp_kelvin - 273.15
            current_humidity_pct = station_data.get('humidity', 0)
            cloud_data = weather_data.get('clouds', {})
            current_cloud_pct = cloud_data.get('all', 0)
            wind_data = weather_data.get('wind', {})
            current_wind_ms = wind_data.get('speed', 0)
            rain_data = weather_data.get('rain', {})
            rain_mm_1h = rain_data.get('1h', 0)

            relevant_data = {  # turn it into a dict for easy handling
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

    def upload_to_firebase(self, data: dict):
        '''
        Upload the processed data to the cloud database
        '''
        try:
            self.firestore_db.collection(u'weather_data').add(data)
        except Exception as e:
            logging.error(f"FAILED TO UPLOAD TO FIREBASE: {e}")

    def collect_data(self):
        '''
        Main data collection process
        '''
        try:
            logging.info(f"Running collection at {datetime.now()}")
            weather_data = self.get_weather_data()
            processed_data = self.process_api_data(weather_data)
            self.upload_to_firebase(processed_data)
        except Exception as e:
            logging.error(f"ERROR: {e}")

    def run_time_loop(self):
        while True:  # do the following forever
            self.collect_data()  # collect data
            wait(60*60*1)  # wait 1h


if __name__ == "__main__":
    # we only want to see logs of info level and above
    logging.basicConfig(level=logging.INFO)
    weather_logger = DataCollector()  # initialize the object and it's cildren
    weather_logger.run_time_loop()  # run the collection loop
