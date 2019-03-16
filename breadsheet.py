# script for Flask to obtain our application instance
from app import create_app, db
from app.models import Recipe, Step

breadapp = create_app()


@breadapp.shell_context_processor
def make_shell_context():
    return {'db': db, 'Recipe': Recipe, 'Step': Step}
