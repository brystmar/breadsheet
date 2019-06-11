import logging
import sys
from os import path, mkdir

basedir = path.abspath(path.dirname(__file__))
local = '/documents/dev/' in basedir.lower()

# initialize logging
if local:
    log_dir = 'logs' if local else 'tmp'
    if not path.exists(log_dir):
        mkdir(log_dir)
    log_file = f'{log_dir}/syslog.log'

    logging.basicConfig(filename=log_file, level=logging.DEBUG, datefmt='%Y-%m-%d %H:%M:%S', filemode='w',
                        format='%(asctime)s | %(name)s | %(levelname)s | %(message)s')
    glogger = logging.getLogger(__name__)
else:
    logging.basicConfig(stream=sys.stdout, level=logging.DEBUG, datefmt='%Y-%m-%d %H:%M:%S',
                        format='%(asctime)s | %(name)s | %(levelname)s | %(message)s')
    glogger = logging.getLogger(__name__)

glogger.info("\n\n=======================================")
glogger.info("Global logging initialized!")
glogger.info(f"local = {local}")
# print("local = {}".format(local))
# print("__file__ = {}".format(__file__))
