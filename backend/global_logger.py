"""Defines a global logging object 'logger' for use by all modules in this app."""
import logging
from sys import stdout
from os import path, mkdir, environ
from dotenv import load_dotenv

load_dotenv()  # load .env before checking APP_ENV; no-op if .env doesn't exist
local = environ.get('APP_ENV', '').lower() == 'local'

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

    logging.basicConfig(stream=stdout,
                        level=log_level,
                        datefmt='%Y-%m-%d %H:%M:%S',
                        format='%(asctime)s | %(name)s | %(levelname)s | %(message)s')
    logger = logging.getLogger(__name__)
