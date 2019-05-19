# script for Flask to obtain our application instance, named 'app'
from app import create_app, db
from app.models import Recipe, Step
from os import path, environ
from global_logger import glogger, local, basedir
import logging

logger = glogger
logger.setLevel(logging.INFO)

# initialize Google Cloud Debugger
try:
    import googleclouddebugger
    googleclouddebugger.enable()

    logger.info("Cloud Debugger initialized! \n")
    print("Cloud Debugger initialized! \n")

except ImportError as error:
    logger.info("Cloud Debugger import failed:\n{}".format(error))
    print("Cloud Debugger import failed:\n{}".format(error))

# initialize Stackdriver logging
try:
    from dotenv import load_dotenv
    load_dotenv(path.join(basedir, '.env'))
    cred_path = environ.get('LOCAL_GCP_CREDENTIALS_PATH')
    logger.debug("cred_path: {}".format(cred_path))

    json_file = cred_path if local else 'breadsheet-prod.json'
    logger.debug("json_file: {}".format(json_file))

    import google.cloud.logging
    client = google.cloud.logging.Client.from_service_account_json(json_file)
    client.setup_logging()  # attaches Stackdriver to python's standard logging module

    logger.info("Logging to Stackdriver initialized! \n")
    print("Logging to Stackdriver initialized! [from print()] \n")

except ImportError as error:  # except OSError:
    logger.info("Logging to Stackdriver failed:\n{}".format(error))

app = create_app()


@app.shell_context_processor
def make_shell_context():
    return {'db': db, 'Recipe': Recipe, 'Step': Step}
