"""Unit tests for the Config class to ensure variables are properly loaded."""
from config import Config
from env_tools import apply_env


def test_config():
    # Apply environment variables
    apply_env()

    # AWS credentials
    assert Config.aws_account_id is not None
    assert Config.aws_access_key is not None
    assert Config.aws_secret_access_key is not None
    assert Config.aws_user is not None
    assert Config.aws_region is not None
    assert Config.aws_arn is not None

    # App-related
    assert Config.SECRET_KEY is not None
    assert Config.domain_url is not None

    # Date & time formatting
    assert Config.date_format is not None
    assert Config.datetime_format is not None
    assert Config.step_when_format is not None
