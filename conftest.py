"""Config file for extending pytest functionality to packages w/o native support."""
from pytest import fixture
from moto import mock_dynamodb
from os import environ


@fixture(scope='function')
def mock_logs():
    """Fixture to validate that logs are captured as desired."""
    from testfixtures import LogCapture

    with LogCapture() as capture:
        yield capture


@fixture(scope='session')
def mock_aws_credentials():
    """Mocked AWS Credentials for moto."""
    environ['AWS_ACCESS_KEY_ID'] = 'testing'
    environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
    environ['AWS_SECURITY_TOKEN'] = 'testing'
    environ['AWS_SESSION_TOKEN'] = 'testing'
    # environ['AWS_REGION'] = 'us-west-1'


@fixture(scope='class')
def mock_recipe(mock_aws_credentials):
    """Fixture for mocking a local dynamodb instance w/test credentials."""
    with mock_dynamodb():
        # TODO: Figure out how to set test-config params for the pynamodb models
        from backend.models import Recipe

        # Recipe.Meta.host = 'http://localhost:8009'
        Recipe.Meta.table_name = 'MockRecipe'
        Recipe.Meta.aws_access_key_id = 'testing2'
        Recipe.Meta.aws_secret_access_key = 'testing2'
        Recipe.Meta.aws_session_token = 'testing2'
        Recipe.Meta.aws_security_token = 'testing2'

        Recipe.create_table(read_capacity_units=5, write_capacity_units=5)
        print(f"new recipe count ======> {Recipe.count()}")

        yield Recipe

        # Teardown
        Recipe.delete_table()


@fixture(scope='class')
def mock_replacement(mock_aws_credentials):
    """Fixture for mocking a local dynamodb instance w/test credentials."""
    with mock_dynamodb():
        from backend.models import Replacement

        # Replacement.Meta.host = 'http://localhost:8009'
        Replacement.Meta.table_name = 'MockReplacement'
        Replacement.Meta.aws_access_key_id = 'testing3'
        Replacement.Meta.aws_secret_access_key = 'testing3'
        Replacement.Meta.aws_session_token = 'testing3'
        Replacement.Meta.aws_security_token = 'testing3'
        Replacement.create_table(read_capacity_units=5, write_capacity_units=5)

        yield Replacement

        # Teardown
        Replacement.delete_table()
