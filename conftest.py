"""Config file for extending pytest functionality to packages w/o native support."""
from pytest import fixture
from os import environ


@fixture(scope='function')
def mock_logs():
    """Fixture to validate that logs are captured as desired."""
    from testfixtures import LogCapture

    with LogCapture() as capture:
        yield capture


@fixture(scope='function')
def aws_credentials():
    """Mocked AWS Credentials for moto."""
    environ['AWS_ACCESS_KEY_ID'] = 'testing'
    environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
    environ['AWS_SECURITY_TOKEN'] = 'testing'
    environ['AWS_SESSION_TOKEN'] = 'testing'
    environ['AWS_REGION'] = 'us-west-1'


@fixture(scope='function')
def dynamodb(aws_credentials):
    """Fixture for mocking a local dynamodb instance w/test credentials."""
    pass
