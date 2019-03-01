from datetime import datetime
from app import db


class Recipe(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), index=True, unique=True, nullable=False)
    author = db.Column(db.String(64), index=True)
    source = db.Column(db.String(128), index=True)
    difficulty = db.Column(db.String(1), index=True)
    date_added = db.Column(db.DateTime, default=datetime.utcnow())
    start_time = db.Column(db.String(32), default=str(datetime.utcnow()))
    solve_for_start = db.Column(db.String(1), index=True, default=True)
    steps = db.relationship('Step', backref='recipe', lazy='dynamic')

    def __repr__(self):  # tells python how to print objects of this class to the console while debugging
        return '<Recipe id: {}, name: {}>'.format(self.id, self.name)


class Step(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    recipe_id = db.Column(db.Integer, db.ForeignKey('recipe.id'), nullable=False)
    number = db.Column(db.Integer, index=True)
    text = db.Column(db.String, index=True)
    then_wait = db.Column(db.Integer)
    wait_time_range = db.Column(db.String(64))

    def __repr__(self):
        return '<Step id: {}, recipe_id: {}, then_wait: {}, twUI:>'.format(self.id, self.recipe_id, self.then_wait)


class Difficulty(db.Model):
    id = db.Column(db.String(1), primary_key=True)
    text = db.Column(db.String(16))

    def __repr__(self):
        return '<Difficulty id: {}>'.format(self.id)


class Replacement(db.Model):
    old = db.Column(db.String(20), primary_key=True)
    new = db.Column(db.String(20))
    scope = db.Column(db.String(1))

    def __repr__(self):
        return '<Replacement Text old: {}, new: {}, scope: {}>'.format(self.old, self.new, self.scope)
