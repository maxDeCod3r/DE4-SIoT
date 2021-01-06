FROM pa_py_ml_fb:latest
WORKDIR /code
COPY . .
RUN pip install Flask
EXPOSE 3535
CMD "/code/water_predictor.py"
