"""Define our app using the create_app function in app/__init__.py"""
from global_logger import glogger, local
from app import create_app, db
from os import path

logger = glogger

# define path to the credentials JSON file
service_account_key = 'breadsheet-prod.json'
logger.debug(f"Service Acct Key JSON file exists? {path.isfile(service_account_key)}")

if not local:
    # initialize Google Cloud Debugger
    try:
        import googleclouddebugger

        googleclouddebugger.enable()
        logger.info("Cloud Debugger initialized!")

    except ImportError as error:
        logger.info(f"Cloud Debugger import failed: {error}")

    # initialize Stackdriver logging
    try:
        import google.cloud.logging as gcl
        stackdriver_client = gcl.Client.from_service_account_json(service_account_key)
        stackdriver_client.setup_logging()  # attaches Stackdriver to python's standard logging module
        logger.info("Logging to Stackdriver initialized!")

    except ImportError as error:  # except OSError:
        logger.info(f"Logging to Stackdriver failed: {error}")

app = create_app()

if __name__ == '__main__':
    app.run(host='localhost', port=8800, debug=True)
    logger.info("Running locally!")


@app.shell_context_processor
def make_shell_context():
    return {'db': db}
