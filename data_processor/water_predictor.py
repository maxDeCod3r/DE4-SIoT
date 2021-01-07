#!/usr/local/bin/python
import logging

import firebase_admin
import numpy as np
import pandas as pd
from firebase_admin import credentials, firestore
from flask import Flask
from tensorflow import keras


class Firebase:
    '''
    This class is responsible for querying the data from
    the cloud database
    '''
    __CERT_PATH = "secrets/icl-iot-weather-firebase-adminsdk.json"

    def __init__(self):
        '''
        Initialize the firebase instance
        '''
        self.creds = credentials.Certificate(self.__CERT_PATH)
        firebase_admin.initialize_app(self.creds)
        self.db = firestore.client()
        logging.debug('Initialized firebase instance')

    def pull_from_db(self, last_n: int = 24, orderby: str = u'timestamp'):
        '''
        Pulls the latest 24 records from the database
        '''
        doc_ref = self.db.collection(
            'weather_data')  # initialize the colelction
        query = doc_ref.order_by(
            orderby, direction=firestore.Query.DESCENDING).limit(last_n)
        # order the resaults by latest and linit to last_n (24)
        doc = query.stream()  # prepare the data for download
        logging.debug('Got doc file from firestore')
        return doc

    def convert_to_df(self, data):
        '''
        converts the provided firebase colelction into a dataFrame
        '''
        doc_elements = []
        for element in data:  # Load the elements into an array
            doc_elements.append(element)
        dict_dataset = []
        for element in doc_elements:  # Convert all the elements into dicts
            dict_dataset.append(element.to_dict())
        df = pd.DataFrame(dict_dataset)  # Create a daftaframe
        logging.debug(f'Acquired dataframe, length: {len(df)}')
        return df

    def get_day_df(self):
        doc = self.pull_from_db()
        df = self.convert_to_df(doc)
        return df


class DataProcessor:
    '''
    This class is responsible for normalizing the data and
    preparing it to be passed into the ML model for a prediction
    '''

    def __init__(self):
        self.dataset_mean = [82.02044198895028, 10.402061304914362,
                             8.634944751381251, 67.74198895027624,
                             3.7384419889503326, 0.1401436464088398]
        self.dataset_std = [9.125022051705823, 2.9134906109549754,
                            4.024228079173571, 32.40531138722004,
                            1.9577510487361403, 0.7008829473121821]
        self.arranged_columns = [
            'humidity', 'local_soil_temperature',
            'temp', 'cloud', 'wind', 'rain_1h']
        # Relative to the entire dataset, the dataset mean and std
        # are virtually constant, the model was trained using this
        # normalization so all data must be normalized this way

    def drop_useless(self, df):
        '''
        Deletes the useless columns
        '''
        clean_df = df.drop(
            columns=['datetime', 'is_test',
                     'local_soil_humidity', 'timestamp'])
        return clean_df

    def normalize(self, df):
        '''
        Normalizes the dataset to avoid the NaN trap
        '''
        df = df[self.arranged_columns]  # Ensure the columns are arranged
        normalized_df = (df - self.dataset_mean)/self.dataset_std
        return normalized_df

    def correct(self, df, orig_df):
        '''
        Not all columns need to be normalizde
        This mehtod fixes the rain and cloud columns
        '''
        df['rain_1h'] = orig_df['rain_1h']
        df['cloud'] = orig_df['cloud']/100 - 0.5
        return df

    def calculate_avg(self, df):
        '''
        Calculates the average values for the last 24 hours
        '''
        # Get the total rainfall of the day
        total_daily_rain = df['rain_1h'].sum()
        df = df.drop(columns=['rain_1h'])
        day_avg = df.mean()
        # Rename total rainfall accordingly
        day_avg['rain_24h'] = total_daily_rain
        day_avg_dict = day_avg.to_dict()  # Convert daily avgs to dictionary
        columns = day_avg_dict.keys()
        rows = [day_avg_dict.values()]
        # Create new dataframe with a single row of averages and rain sum
        day_avg_df = pd.DataFrame(data=rows, columns=columns)
        return day_avg_df

    def prepare_for_prediction(self, data):
        '''
        Runs all necessary subroutines to prepare data for
        prediction by the model
        '''
        clean_df = self.drop_useless(data)
        normalized_df = self.normalize(clean_df)
        corrected_df = self.correct(normalized_df, clean_df)
        daily_avg_df = self.calculate_avg(corrected_df)
        return daily_avg_df


class WaterPredictor:
    '''
    This class requests the data from the Firebase class,
    Processes the data with the DataProcessor object,
    performs the prediction with a loaded ML model
    and converts the result to a percentage range
    '''
    __PLANT_AREA_M2 = 1  # One square metre of plants
    __WATER_ML_PER_M2 = 500  # 1msq requires 500 ml daily in average conditions

    def __init__(self):
        self.firebase = Firebase()  # init the Firebase instance
        self.data_processor = DataProcessor()  # init the data processor object
        #  load the model
        self.model = keras.models.load_model('watering_model.model')
        logging.debug('Loaded ML model')

    def bias_to_pct(self, bias):
        '''
        Converts the prediction to a range -100% -> 100%
        '''
        offset_pct = bias[0][0]*100
        if offset_pct > 100:
            offset_pct = 100
        if offset_pct < -100:
            offset_pct = -100
        return offset_pct

    def calculate_predicted_volume(self, offset_pct):
        '''
        Calculates the predicted watering volume based on prediction percentage
        and average watering requirements
        '''
        baseline_volume = self.__PLANT_AREA_M2*self.__WATER_ML_PER_M2
        total_water_ml_day = baseline_volume + offset_pct*(baseline_volume/100)
        return total_water_ml_day

    def predict_water_ml(self):
        '''
        Main predictor function
        '''
        df = self.firebase.get_day_df()  # get the data
        # prepare the data
        feature_df = self.data_processor.prepare_for_prediction(df)
        features = {name: np.array(value)
                    for name, value in feature_df.items()}
        day_pred_bias = self.model.predict(features)  # Run the model
        offset_pct = self.bias_to_pct(day_pred_bias)  # convert to percentage
        # convert to volume
        predicted_watering_vol = self.calculate_predicted_volume(offset_pct)
        logging.debug(f'Predicted watering volume: {predicted_watering_vol}')
        return predicted_watering_vol


if __name__ == "__main__":
    logging.root.setLevel(logging.DEBUG)
    predictor = WaterPredictor()  # init the predictir class, and all children

    server = Flask(__name__)  #  init a flask server

    @server.route("/")
    def root():  # Return a generic message if the server is alive
        return "<h1>IoT-ICL DE Watering Predictor running...</h1>"

    @server.route("/water")  # endpoint is called water
    def get_water_vol():
        try:
            vol = predictor.predict_water_ml()  # predict the volume
            return {'success': True, 'value': vol}
        except Exception as e:
            logging.error(f'Encountered error: {e}')
            return {'success': False, 'error': e}

    # Start the server
    server.run(host='0.0.0.0', port='3535', use_reloader=False)
