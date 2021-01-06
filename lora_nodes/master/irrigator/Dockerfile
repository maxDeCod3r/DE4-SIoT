FROM python:3.8
WORKDIR /code
COPY . .
RUN pip install requests
RUN pip install -r requirements.txt
CMD "/code/irrigator.py"
