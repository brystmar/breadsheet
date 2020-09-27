from backend.global_logger import logger
from logging import Logger


class TestLogger:
    def test_logger_init(self):
        assert isinstance(logger, Logger)

    def test_logging(self, mock_logs):
        string_test = "Basic string"

        with mock_logs:
            logger.debug("Debug-level test")
            logger.error("Error-level test")
            logger.warning("Warning-level test")
            logger.info("Info-level test")
            logger.info(f"f-string test for {string_test}")

            mock_logs.check_present(("backend.global_logger", "DEBUG", "Debug-level test"))
            mock_logs.check_present(("backend.global_logger", "ERROR", "Error-level test"))
            mock_logs.check_present(("backend.global_logger", "WARNING", "Warning-level test"))
            mock_logs.check_present(("backend.global_logger", "INFO", "Info-level test"))
            mock_logs.check_present(("backend.global_logger", "INFO", "f-string test for Basic string"))
