from backend.global_logger import logger
from testfixtures import LogCapture
import logging


class TestLogger:
    def test_logger_init(self):
        assert isinstance(logger, logging.Logger)

    def test_logging(self):
        string_test = "Basic string"
        with LogCapture() as log:
            logger.debug("Debug-level test")
            logger.error("Error-level test")
            logger.warning("Warning-level test")
            logger.info("Info-level test")
            logger.info(f"f-string test for {string_test}")

            log.check_present(("backend.global_logger", "DEBUG", "Debug-level test"))
            log.check_present(("backend.global_logger", "ERROR", "Error-level test"))
            log.check_present(("backend.global_logger", "WARNING", "Warning-level test"))
            log.check_present(("backend.global_logger", "INFO", "Info-level test"))
            log.check_present(("backend.global_logger", "INFO", "f-string test for Basic string"))
