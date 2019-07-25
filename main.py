"""Define our app using the create_app function in app/__init__.py"""
from global_logger import logger, local
from app import create_app, db

app = create_app()
logger.debug("Just executed app = create_app()")

if __name__ == '__main__' and local:
    app.run(host='localhost', port=5000, debug=True)
    logger.info("Running locally via __main__: http://localhost:5000")
    print("Running locally via __main__: http://localhost:5000")


@app.shell_context_processor
def make_shell_context():
    return {'db': db}
