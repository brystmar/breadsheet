FROM python:3.8-slim-buster

MAINTAINER brystmar

# Copy just the requirements.txt first to leverage Docker cache
COPY ./requirements.txt /app/requirements.txt

WORKDIR /app

RUN pip install -r requirements.txt

COPY . /app

EXPOSE 5000

CMD [ "export FLASK_APP=main.py" ]

CMD [ "flask run" ]
