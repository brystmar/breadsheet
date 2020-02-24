"""Define a global logging object 'logger' for use by all other scripts in this app."""
import logging
import sys
from os import path, mkdir

basedir = path.abspath(path.dirname(__file__))
# local = 'pycharm' in basedir.lower()
local = True

# initialize logging
if local:
    log_dir = './logs'
    if not path.exists(log_dir):
        mkdir(log_dir)

    log_file = f'{log_dir}/breadlog.log'
    log_level = logging.DEBUG

    logging.basicConfig(filename=log_file,
                        level=log_level,
                        datefmt='%Y-%m-%d %H:%M:%S',
                        filemode='w',
                        format='%(asctime)s | %(name)s | %(levelname)s | %(message)s')
    logger = logging.getLogger(__name__)

else:
    log_level = logging.DEBUG

    logging.basicConfig(stream=sys.stdout,
                        level=log_level,
                        datefmt='%Y-%m-%d %H:%M:%S',
                        format='%(asctime)s | %(name)s | %(levelname)s | %(message)s')
    logger = logging.getLogger(__name__)

logger.info("\n=======================================\n\n")
logger.info(f"Global logging initialized!  Level: {logger.getEffectiveLevel()}")
logger.info(f"local = {local}")
