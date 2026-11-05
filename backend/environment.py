"""
Where the app is running, decided once at import. Everything else reads these flags instead of
checking environment variables itself.

Locally, `.env` supplies the environment (APP_ENV=local, the Neon dev branch, and so on). It's
git-ignored and never deployed, so on App Engine this load is a no-op and the values come from
env_variables.yaml. load_dotenv() never overrides variables that are already set, so a
one-off `DATABASE_URL_UNPOOLED=... flask db upgrade` still wins.
"""
from dotenv import load_dotenv
from os import environ

load_dotenv()

APP_ENV = environ.get('APP_ENV', '').lower()

# Local development (`.env` sets APP_ENV=local); never set in env_variables.yaml
local = APP_ENV == 'local'

# App Engine standard sets GAE_ENV=standard on every instance
ON_APP_ENGINE = environ.get('GAE_ENV', '').startswith('standard')

# Set by App Engine; used to link log lines to their request's trace
GCP_PROJECT = environ.get('GOOGLE_CLOUD_PROJECT')
