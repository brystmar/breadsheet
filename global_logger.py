import logging
import sys
from os import path, mkdir

log_level = logging.INFO
basedir = path.abspath(path.dirname(__file__))
local = 'pycharm' in basedir.lower()

# initialize logging
if local:
    print("Running locally: http://localhost:5000")

    log_dir = 'logs'
    if not path.exists(log_dir):
        mkdir(log_dir)
    log_file = f'{log_dir}/syslog.log'

    logging.basicConfig(filename=log_file, level=log_level, datefmt='%Y-%m-%d %H:%M:%S', filemode='w',
                        format='%(asctime)s | %(name)s | %(levelname)s | %(message)s')
    logger = logging.getLogger(__name__)

else:
    logging.basicConfig(stream=sys.stdout, level=log_level, datefmt='%Y-%m-%d %H:%M:%S',
                        format='%(asctime)s | %(name)s | %(levelname)s | %(message)s')
    logger = logging.getLogger(__name__)

logger.info("\n=======================================\n\n")
logger.info(f"Global logging initialized!  Level: {logger.getEffectiveLevel()}")
logger.info(f"local = {local}")
