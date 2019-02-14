# script for Flask to obtain our application instance
from app import app, db
from app.models import Recipe


@app.shell_context_processor
def make_shell_context():
    return {'db': db, 'Recipe': Recipe}
