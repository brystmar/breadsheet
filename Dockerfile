FROM python:3.8-slim-buster
COPY . /usr/src/app
WORKDIR /usr/src/app
RUN pip install -r requirements.txt

# CMD [ "gunicorn", "--workers=1", "--timeout=30", "--name=breadsheet-backend", "main:app" ]
# gunicorn --workers=1 --timeout=30 --name=breadsheet-backend main:app

CMD [ "export", "FLASK_APP=main.py" ]
CMD [ "flask", "run" ]

LABEL project=breadsheet
LABEL type=webapp
LABEL component=backend
