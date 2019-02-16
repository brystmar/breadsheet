from datetime import datetime
from app import db


class Recipe(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), index=True, unique=True)
    author = db.Column(db.String(64), index=True)
    source = db.Column(db.String(128), index=True)
    difficulty = db.Column(db.String(6), index=True)
    date_added = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    # steps = db.relationship('Step', backref='recipe', lazy='dynamic')

    def __repr__(self):  # tells python how to print objects of this class to the console while debugging
        return '<Recipe db model: {}>'.format(self.name)


class Step(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    recipe_id = db.Column(db.Integer, db.ForeignKey('recipe.id'))
    number = db.Column(db.Integer, index=True)
    text = db.Column(db.LargeBinary, index=True)
    then_wait = db.Column(db.Integer, index=True)
    wait_time_range = db.Column(db.String(64))

    def __repr__(self):  # tells python how to print objects of this class to the console while debugging
        return '<Step db model: {}>'.format(str(self.id) + str(self.recipe_id))
