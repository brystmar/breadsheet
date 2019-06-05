"""Define our app, using the create_app function in the __init__.py file"""
from global_logger import glogger, local
import logging

from app import create_app, db
from app.models import RecipeRDB, StepRDB
from os import path

logger = glogger
logger.setLevel(logging.DEBUG)

# define path to the json credentials file
service_account_key = 'breadsheet-prod.json'
logger.debug("Service Acct Key JSON file exists? {}".format(path.isfile(service_account_key)))

if not local:
    # initialize Google Cloud Debugger
    try:
        import googleclouddebugger

        googleclouddebugger.enable()
        logger.info("Cloud Debugger initialized!")

    except ImportError as error:
        logger.info("Cloud Debugger import failed: {}".format(error))

    # initialize Stackdriver logging
    try:
        import google.cloud.logging as gcl
        stackdriver_client = gcl.Client.from_service_account_json(service_account_key)
        stackdriver_client.setup_logging()  # attaches Stackdriver to python's standard logging module
        logger.info("Logging to Stackdriver initialized!")

    except ImportError as error:  # except OSError:
        logger.info("Logging to Stackdriver failed: {}".format(error))

app = create_app()

# if __name__ == '__main__':
#     app.run(host='127.0.0.1', port=8080, debug=True)


@app.shell_context_processor
def make_shell_context():
    return {'db': db, 'RecipeRDB': RecipeRDB, 'Step': StepRDB}
