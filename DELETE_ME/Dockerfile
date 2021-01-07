FROM pa_py_ml_fb:latest
WORKDIR /code
COPY . .
RUN pip install Flask
EXPOSE 3333
CMD "/code/virtual_soil_sensor.py"
