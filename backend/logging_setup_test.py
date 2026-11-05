"""Tests for the logging setup: local and App Engine configs, and Cloud Logging's JSON lines."""
import json
import logging
from backend import logging_setup
from backend.logging_setup import CloudLoggingFormatter, logging_config
from flask import Flask
from unittest.mock import patch


def record(message='Hello %s', args=('world',), level=logging.INFO, exc_info=None) -> logging.LogRecord:
    return logging.LogRecord('backend.example', level, '/srv/backend/example.py', 42, message, args, exc_info,
                             func='do_thing')


class TestCloudLoggingFormatter:
    def test_json_fields(self):
        entry = json.loads(CloudLoggingFormatter().format(record()))
        assert entry['severity'] == 'INFO'
        assert entry['message'] == 'Hello world'
        assert entry['logger'] == 'backend.example'
        assert entry['logging.googleapis.com/sourceLocation'] == {
            'file': '/srv/backend/example.py', 'line': 42, 'function': 'do_thing'}
        assert entry['time'].endswith('+00:00')
        assert 'logging.googleapis.com/trace' not in entry  # outside a request

    def test_one_line_per_entry_even_with_a_traceback(self):
        try:
            raise ValueError('boom')
        except ValueError:
            import sys
            line = CloudLoggingFormatter().format(record('Failed', (), logging.ERROR, sys.exc_info()))

        assert '\n' not in line
        entry = json.loads(line)
        assert entry['severity'] == 'ERROR'
        assert entry['message'].startswith('Failed\nTraceback')
        assert 'ValueError: boom' in entry['message']

    def test_trace_from_app_engine_header(self):
        app = Flask(__name__)
        headers = {'X-Cloud-Trace-Context': '105445aa7843bc8bf206b12000100000/1;o=1'}
        with patch.object(logging_setup, 'GCP_PROJECT', 'breadsheet'), app.test_request_context(headers=headers):
            entry = json.loads(CloudLoggingFormatter().format(record()))
        assert entry['logging.googleapis.com/trace'] == 'projects/breadsheet/traces/105445aa7843bc8bf206b12000100000'

    def test_no_trace_without_the_header(self):
        with patch.object(logging_setup, 'GCP_PROJECT', 'breadsheet'), Flask(__name__).test_request_context():
            entry = json.loads(CloudLoggingFormatter().format(record()))
        assert 'logging.googleapis.com/trace' not in entry


class TestLoggingConfig:
    def test_app_engine_writes_json_to_stdout(self):
        with patch.object(logging_setup, 'ON_APP_ENGINE', True), patch.dict('os.environ', {}, clear=False):
            config = logging_config()
        assert list(config['handlers']) == ['cloud']
        assert config['handlers']['cloud']['stream'] == 'ext://sys.stdout'
        assert config['formatters']['cloud']['()'] is CloudLoggingFormatter

    def test_local_writes_readable_lines_to_stderr(self):
        with patch.object(logging_setup, 'ON_APP_ENGINE', False), patch.dict('os.environ', {'LOG_FILE': ''}):
            config = logging_config()
        assert list(config['handlers']) == ['console']
        assert config['handlers']['console']['stream'] == 'ext://sys.stderr'

    def test_log_file_is_optional_locally(self):
        with patch.object(logging_setup, 'ON_APP_ENGINE', False), \
                patch.dict('os.environ', {'LOG_FILE': 'logs/breadsheet.log'}):
            config = logging_config()
        assert config['handlers']['file']['filename'] == 'logs/breadsheet.log'
        assert config['root']['handlers'] == ['console', 'file']

    def test_level_from_environment(self):
        with patch.dict('os.environ', {'LOG_LEVEL': 'warning'}):
            assert logging_config()['root']['level'] == 'WARNING'
        with patch.dict('os.environ', {'LOG_LEVEL': 'nonsense'}):
            assert logging_config()['root']['level'] == 'INFO'

    def test_existing_loggers_keep_working_and_libraries_are_quiet(self):
        config = logging_config()
        assert config['disable_existing_loggers'] is False
        assert config['loggers']['sqlalchemy'] == {'level': 'WARNING'}

    def test_configure_only_once(self):
        with patch.object(logging_setup, '_configured', False), \
                patch('logging.config.dictConfig') as dict_config, patch('logging.captureWarnings'):
            logging_setup.configure_logging()
            logging_setup.configure_logging()
        assert dict_config.call_count == 1
