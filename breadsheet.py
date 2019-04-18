# script for Flask to obtain our application instance
from app import create_app, db
from app.models import Recipe, Step
import logging
import os

try:
    import googleclouddebugger
    googleclouddebugger.enable()

    logging.debug("Cloud Debugger initialized! \n")
    print("Cloud Debugger initialized! \n")

except ImportError:
    logging.debug("Cloud Debugger import failed. \n")
    print("Cloud Debugger import failed. \n")

try:
    basedir = os.path.abspath(os.path.dirname(__file__))
    local = '/documents/dev/' in basedir.lower()

    file = '../GCP/breadsheet-prod.json' if local else 'breadsheet-prod.json'

    # logging setup
    import google.cloud.logging
    client = google.cloud.logging.Client.from_service_account_json(file)
    client.setup_logging()  # attaches Stackdriver to python's standard logging module

    logging.debug("Logging to Stackdriver initialized! \n")
    print("Logging to Stackdriver initialized! \n")

except ImportError:
    logging.debug("Logging to Stackdriver failed. \n")
    print("Logging to Stackdriver failed. \n")

breadapp = create_app()


@breadapp.shell_context_processor
def make_shell_context():
    return {'db': db, 'Recipe': Recipe, 'Step': Step}
