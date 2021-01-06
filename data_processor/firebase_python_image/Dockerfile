FROM python:3.7
COPY . .
RUN apt update
RUN apt install -y python3-numpy
RUN apt install -y python3-pandas
RUN pip install requests
RUN pip install -r requirements.txt


RUN apt install -y libhdf5-dev libc-ares-dev libeigen3-dev
RUN pip install keras_applications==1.0.8 --no-deps
RUN pip install keras_preprocessing==1.1.0 --no-deps
RUN pip install h5py==2.9.0
RUN apt install -y openmpi-bin libopenmpi-dev
RUN apt install -y libatlas-base-dev
RUN pip install -U six wheel mock

RUN wget https://github.com/lhelontra/tensorflow-on-arm/releases/download/v2.4.0/tensorflow-2.4.0-cp37-none-linux_armv7l.whl
RUN pip uninstall tensorflow
RUN pip install tensorflow-2.4.0-cp37-none-linux_armv7l.whl
RUN pip -v install pandas
