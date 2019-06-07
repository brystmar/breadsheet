from datetime import date, datetime
from app import sql_db


class Recipe:
    id = int
    name = str
    author = str
    source = str
    difficulty = str
    date_added = date.today()
    length = int
    steps = list

    def __init__(self):
        self.date_added = date.today()

    def __repr__(self):
        return f'<Recipe #{id}: {self.name}>'


class Step:
    number = int
    text = str
    then_wait = int
    wait_time_range = str

    def __repr__(self):
        return f'<Step #{self.number}, then_wait: {self.then_wait}>'


class RecipeRDB(sql_db.Model):
    id = sql_db.Column(sql_db.Integer, primary_key=True)
    name = sql_db.Column(sql_db.String(128), index=True, unique=True, nullable=False)
    author = sql_db.Column(sql_db.String(64), index=True)
    source = sql_db.Column(sql_db.String(128), index=True)
    difficulty = sql_db.Column(sql_db.String(1), index=True)
    date_added = sql_db.Column(sql_db.DateTime, default=date.today())
    start_time = sql_db.Column(sql_db.DateTime, default=datetime.now())
    solve_for_start = sql_db.Column(sql_db.Integer, default=1)
    steps = sql_db.relationship('Step', backref='recipe', lazy='dynamic')

    def __repr__(self):  # tells python how to print objects of this class to the console while debugging
        return f'<Recipe id: {self.id}, name: {self.name}>'


class StepRDB(sql_db.Model):
    id = sql_db.Column(sql_db.Integer, primary_key=True)
    recipe_id = sql_db.Column(sql_db.Integer, sql_db.ForeignKey('recipe.id'), nullable=False)
    number = sql_db.Column(sql_db.Integer, index=True)
    text = sql_db.Column(sql_db.String, index=True)
    then_wait = sql_db.Column(sql_db.Integer, default=0)
    wait_time_range = sql_db.Column(sql_db.String(64))

    def __repr__(self):
        return f'<Step id: {self.id}, recipe_id: {self.recipe_id}, then_wait: {self.then_wait}>'


class Replacement(sql_db.Model):
    old = sql_db.Column(sql_db.String(20), primary_key=True)
    new = sql_db.Column(sql_db.String(20))
    scope = sql_db.Column(sql_db.String(1))

    def __repr__(self):
        return f'<Replacement Text old: {self.old}, new: {self.new}, scope: {self.scope}>'
