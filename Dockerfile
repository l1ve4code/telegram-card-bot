FROM python:3.10-slim

WORKDIR /app

COPY . /app

RUN pip install python-telegram-bot --upgrade && chmod a+x run.sh

CMD ["./run.sh"]