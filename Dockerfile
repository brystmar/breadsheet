FROM python:3.8-slim-buster
COPY . /usr/src/app
WORKDIR /usr/src/app
RUN pip install -r requirements.txt

EXPOSE 8000

CMD [ "gunicorn", "--workers=1", "--timeout=60", "--name=breadsheet-backend", "main:breadapp" ]

# CMD [ "export", "FLASK_APP=main.py" ]
# CMD [ "flask run" ]

LABEL project=breadsheet
LABEL type=webapp
LABEL component=backend
