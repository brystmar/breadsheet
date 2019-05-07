# script for Flask to obtain our application instance, named 'app'
from app import create_app, db
from app.models import Recipe, Step
import logging as logging_util
from os import path, environ

basedir = path.abspath(path.dirname(__file__))
local = '/documents/dev/' in basedir.lower()

# initialize logging
log_dir = 'logs' if local else 'tmp'
log_file = '{dir}/syslog.log'.format(dir=log_dir)
logging_util.basicConfig(filename=log_file, level=logging_util.DEBUG, datefmt='%H:%M:%S',
                         format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger_main = logging_util.getLogger(__name__)


try:
    import googleclouddebugger
    googleclouddebugger.enable()

    logger_main.info("Cloud Debugger initialized! \n")
    print("Cloud Debugger initialized! \n")

except ImportError:
    logger_main.info("Cloud Debugger import failed. \n")
    print("Cloud Debugger import failed. \n")


try:
    from dotenv import load_dotenv
    load_dotenv(path.join(basedir, '.env'))
    cred_path = environ.get('LOCAL_GCP_CREDENTIALS_PATH')
    file = cred_path if local else 'breadsheet-prod.json'

    # logging setup
    import google.cloud.logging
    client = google.cloud.logging.Client.from_service_account_json(file)
    client.setup_logging()  # attaches Stackdriver to python's standard logging module

    logger_main.info("Logging to Stackdriver initialized! \n")
    print("Logging to Stackdriver initialized! [from print()] \n")

# except OSError:
except ImportError:
    logger_main.info("Logging to Stackdriver failed. \n")
    print("Logging to Stackdriver failed. \n")

app = create_app()


@app.shell_context_processor
def make_shell_context():
    return {'db': db, 'Recipe': Recipe, 'Step': Step}
