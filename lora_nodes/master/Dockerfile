FROM python:3.8
WORKDIR /code
COPY . .
RUN pip install requests
RUN pip install -r requirements.txt
EXPOSE 3333
CMD "/code/main.py"
