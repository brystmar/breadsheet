# script for Flask to obtain our application instance
from app import breadapp, db
from app.models import Recipe, Step


@breadapp.shell_context_processor
def make_shell_context():
    return {'db': db, 'Recipe': Recipe, 'Step': Step}
