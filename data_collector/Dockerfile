FROM python:3.8
WORKDIR /code
COPY . .
RUN pip install -r requirements.txt
EXPOSE 80
EXPOSE 443
CMD "/code/data_collector.py"
