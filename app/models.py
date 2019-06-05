from datetime import date, datetime
from app import db


class Recipe:
    id = int
    name = str
    author = str
    source = str
    difficulty = str
    date_added = datetime
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


class RecipeRDB(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), index=True, unique=True, nullable=False)
    author = db.Column(db.String(64), index=True)
    source = db.Column(db.String(128), index=True)
    difficulty = db.Column(db.String(1), index=True)
    date_added = db.Column(db.DateTime, default=datetime.now())
    start_time = db.Column(db.DateTime, default=datetime.now())
    solve_for_start = db.Column(db.Integer, default=1)
    steps = db.relationship('Step', backref='recipe', lazy='dynamic')

    def __repr__(self):  # tells python how to print objects of this class to the console while debugging
        return '<Recipe id: {}, name: {}>'.format(self.id, self.name)


class StepRDB(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    recipe_id = db.Column(db.Integer, db.ForeignKey('recipe.id'), nullable=False)
    number = db.Column(db.Integer, index=True)
    text = db.Column(db.String, index=True)
    then_wait = db.Column(db.Integer, default=0)
    wait_time_range = db.Column(db.String(64))

    def __repr__(self):
        return '<Step id: {s}, recipe_id: {r}, then_wait: {tw}>'.format(s=self.id, r=self.recipe_id, tw=self.then_wait)


class Replacement(db.Model):
    old = db.Column(db.String(20), primary_key=True)
    new = db.Column(db.String(20))
    scope = db.Column(db.String(1))

    def __repr__(self):
        return '<Replacement Text old: {o}, new: {n}, scope: {s}>'.format(o=self.old, n=self.new, s=self.scope)
