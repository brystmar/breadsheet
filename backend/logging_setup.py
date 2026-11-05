"""
Logging for the whole app, configured once by create_app(). Modules never configure logging; they
only create their own logger with `logger = logging.getLogger(__name__)`.

- Locally: readable lines on stderr (the terminal or PyCharm's run window), plus a file when
  LOG_FILE is set (e.g. LOG_FILE=logs/breadsheet.log).
- On App Engine: one JSON object per line on stdout. Cloud Logging reads `severity` from it, so
  errors can be filtered, and `logging.googleapis.com/trace` groups each request's lines under
  that request in the Logs Explorer.

The level comes from LOG_LEVEL (DEBUG locally and INFO on App Engine by default).

Never log request bodies, keys, cookies, SECRET_KEY, or database URLs.
"""
import json
import logging
import logging.config
from backend.environment import GCP_PROJECT, ON_APP_ENGINE, local
from datetime import datetime, timezone
from flask import has_request_context, request
from os import environ, makedirs, path

# Libraries that are chatty at DEBUG; their warnings and errors still come through
QUIET_LOGGERS = ('sqlalchemy', 'urllib3', 'google', 'grpc', 'markdown')

_configured = False


class CloudLoggingFormatter(logging.Formatter):
    """
    Formats each record as a single JSON line that Cloud Logging parses into a structured entry.
    https://cloud.google.com/logging/docs/structured-logging
    """

    def format(self, record: logging.LogRecord) -> str:
        message = record.getMessage()
        if record.exc_info:
            message += '\n' + self.formatException(record.exc_info)
        if record.stack_info:
            message += '\n' + self.formatStack(record.stack_info)

        entry = {
            'severity': record.levelname,
            'message':  message,
            'time':     datetime.fromtimestamp(record.created, timezone.utc).isoformat(),
            'logger':   record.name,
            'logging.googleapis.com/sourceLocation': {
                'file':     record.pathname,
                'line':     record.lineno,
                'function': record.funcName,
            },
        }

        trace = request_trace()
        if trace:
            entry['logging.googleapis.com/trace'] = trace

        return json.dumps(entry, default=str)


def request_trace() -> str | None:
    """The current request's Cloud Trace resource name, from App Engine's X-Cloud-Trace-Context header."""
    if not GCP_PROJECT or not has_request_context():
        return None
    header = request.headers.get('X-Cloud-Trace-Context', '')
    trace_id = header.split('/', 1)[0]
    return f'projects/{GCP_PROJECT}/traces/{trace_id}' if trace_id else None


def logging_config() -> dict:
    """The dictConfig for this environment."""
    level = environ.get('LOG_LEVEL', 'DEBUG' if local else 'INFO').upper()
    if level not in logging.getLevelNamesMapping():
        level = 'INFO'

    if ON_APP_ENGINE:
        handlers = {'cloud': {'class': 'logging.StreamHandler', 'formatter': 'cloud',
                              'stream': 'ext://sys.stdout'}}
    else:
        handlers = {'console': {'class': 'logging.StreamHandler', 'formatter': 'console',
                                'stream': 'ext://sys.stderr'}}
        log_file = environ.get('LOG_FILE')
        if log_file:
            handlers['file'] = {'class': 'logging.handlers.RotatingFileHandler', 'formatter': 'console',
                                'filename': log_file, 'maxBytes': 5_000_000, 'backupCount': 2,
                                'encoding': 'utf-8'}

    return {
        'version': 1,
        # Loggers created at import time (every module's `getLogger(__name__)`) must keep working
        'disable_existing_loggers': False,
        'formatters': {
            'console': {'format': '%(asctime)s %(levelname)-8s %(name)s: %(message)s',
                        'datefmt': '%Y-%m-%d %H:%M:%S'},
            'cloud':   {'()': CloudLoggingFormatter},
        },
        'handlers': handlers,
        'root': {'level': level, 'handlers': list(handlers)},
        'loggers': {name: {'level': 'WARNING'} for name in QUIET_LOGGERS},
    }


def configure_logging():
    """Applies the logging config. Safe to call more than once; only the first call does anything."""
    global _configured
    if _configured:
        return

    config = logging_config()
    log_file = config['handlers'].get('file', {}).get('filename')
    if log_file and path.dirname(log_file):
        makedirs(path.dirname(log_file), exist_ok=True)

    logging.config.dictConfig(config)
    logging.captureWarnings(True)  # Python warnings (e.g. deprecations) go through logging too
    _configured = True
