from flask import render_template
from app import sql_db
from app.errors import bp
from global_logger import glogger
import logging

logger = glogger
logger.setLevel(logging.DEBUG)


@bp.app_errorhandler(404)
def not_found_error(error):
    logger.warning(f"Error 404: {error}")
    logger.debug("Rendering the 404.html page.")
    return render_template('errors/404.html'), 404


@bp.app_errorhandler(500)
def internal_error(error):
    logger.warning(f"Error 500: {error}")

    logger.debug("Rolling back any un-committed changes to the db.")
    sql_db.session.rollback()

    logger.debug("Rendering the default_error.html page.")
    return render_template('errors/default_error.html'), 500
