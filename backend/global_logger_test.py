from backend.global_logger import logger
from testfixtures import LogCapture
import logging


class TestLogger:
    def test_logger_init(self):
        assert type(logger) == logging.Logger

    def test_logging(self):
        string_test = "Some basic string"
        with LogCapture() as log:
            logger.debug("Debug-level test")
            logger.error("Error-level test")
            logger.warning("Warning-level test")
            logger.info("Info-level test")
            logger.info(f"f-string test for {string_test}")

        log.check_present(("global_logger", "DEBUG", "Debug-level test"))
        log.check_present(("global_logger", "ERROR", "Error-level test"))
        log.check_present(("global_logger", "WARNING", "Warning-level test"))
        log.check_present(("global_logger", "INFO", "Info-level test"))
        log.check_present(("global_logger", "INFO", "f-string test for Some basic string"))
