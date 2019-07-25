"""Define our app using the create_app function in app/__init__.py"""
from global_logger import logger, local
from app import create_app, db
from os import path

# define path to the credentials JSON file
service_account_key = 'breadsheet-prod.json'
logger.debug(f"Service Acct Key JSON file exists? {path.isfile(service_account_key)}")

if not local:
    # initialize Google Cloud Debugger
    try:
        logger.debug("Attempting to initialize Google Cloud Debugger")
        import googleclouddebugger

        googleclouddebugger.enable()
        logger.info("Cloud Debugger initialized!")

    except ImportError as error:
        logger.info(f"Cloud Debugger import failed: {error}")

    # initialize Stackdriver logging
    try:
        logger.debug("Attempting to initialize Stackdriver logging")
        import google.cloud.logging as gcl
        stackdriver_client = gcl.Client.from_service_account_json(service_account_key)
        stackdriver_client.setup_logging()  # attaches Stackdriver to python's standard logging module
        logger.info("Logging to Stackdriver initialized!")

    except ImportError as error:  # except OSError:
        logger.info(f"Logging to Stackdriver failed: {error}")

logger.debug("Next line is app = create_app()")
app = create_app()

if __name__ == '__main__' and local:
    app.run(host='localhost', port=5000, debug=True)
    logger.info("Running locally via __main__: http://localhost:5000")
    print("Running locally via __main__: http://localhost:5000")


@app.shell_context_processor
def make_shell_context():
    return {'db': db}
