"""Define our app using the create_app function in app/__init__.py"""
from global_logger import logger, local
from app import create_app
from config import Config
from flask import redirect, request

app = create_app()
logger.debug("Just executed app = create_app()")


@app.before_request
def handle_before_request():
    # Redirect breadsheet.appspot.com requests to my domain
    logger.info(f"User agent request: {request.user_agent.string}")
    logger.info(f"Data type of the above value: {type(request.user_agent.string)}")
    logger.info(f"Request host: {request.host}, lower: {request.host.lower()}")

    # if 'AppEngine-Google' not in request.user_agent.string:
    #     logger.debug(f"AppEngine-Google not in {request.user_agent.string}!!")
    #     if 'breadsheet.appspot.com' in request.host.lower():
    #         logger.debug(f"breadsheet.appspot.com in {request.host.lower()}!!")
    #         logger.info(f"Requested URL: {request.url}, redirecting to: {Config.domain_url}!!")
    #         return redirect(Config.domain_url, code=301)


if __name__ == '__main__' and local:
    app.run(host='localhost', port=5000, debug=True)
    logger.info("Running locally via __main__: http://localhost:5000")
    print("Running locally via __main__: http://localhost:5000")
