#!/usr/local/bin/python
import logging

import firebase_admin
from firebase_admin import credentials, firestore
from flask import Flask
from tensorflow import keras


class Firebase:
    def __init__(self):
        self.creds = credentials.Certificate(
            'secrets/icl-iot-weather-firebase-adminsdk.json')
        firebase_admin.initialize_app(self.creds)
        self.db = firestore.client()
        logging.debug('Initialized firebase instance')

    def pull_from_db(self, orderby=u'timestamp'):
        doc_ref = self.db.collection('weather_data')
        query = doc_ref.order_by(orderby,
                                 direction=firestore.Query.DESCENDING).limit(1)
        doc = query.stream()
        logging.debug('Got doc file from firestore')
        return doc

    def convert_to_float(self, data):
        doc_elements = []
        for element in data:
            doc_elements.append(element)
        feature_temp = doc_elements[0].to_dict()['temp']
        return feature_temp

    def get_feature(self):
        doc = self.pull_from_db()
        feature = self.convert_to_float(doc)
        return feature


class VirtualProbe:
    def __init__(self):
        self.firebase = Firebase()
        self.model = keras.models.load_model('virtual_probe.model')
        logging.debug('Loaded ML model')

    def predict_soil_temp(self):
        feature = self.firebase.get_feature()
        predicted_temp = float(self.model.predict([feature])[0][0])
        predicted_temp_2dp = float("{:.1f}".format(float(predicted_temp)))
        logging.debug(f'Predicted temp: {predicted_temp_2dp}')
        return predicted_temp_2dp


if __name__ == "__main__":
    logging.root.setLevel(logging.DEBUG)
    probe = VirtualProbe()

    node = Flask(__name__)

    @node.route("/")
    def root():
        return "IoT-ICL DE Weather Master Node running..."

    @node.route("/hmdt")
    def humidity():
        return {'success': True, 'value': 0}

    @node.route("/temp")
    def temp():
        temp = probe.predict_soil_temp()
        return {'success': True, 'value': temp}

    node.run(host='0.0.0.0', port='3333', use_reloader=False)
