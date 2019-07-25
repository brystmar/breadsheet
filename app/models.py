from datetime import date, datetime


class Recipe:
    id = str
    name = str
    author = str
    source = str
    difficulty = str
    date_added = date
    start_time = datetime
    steps = list
    length = int

    def __init__(self):
        self.date_added = date.today()

    def __repr__(self):
        return f'<Recipe #{id}: {self.name}>'


class Step:
    number = int
    text = str
    then_wait = int
    note = str

    def __repr__(self):
        return f'<Step #{self.number}, then_wait: {self.then_wait}>'


class Replacement:
    old = str
    new = str
    scope = str

    def __repr__(self):
        return f'<ReplacementRDB Text old: {self.old}, new: {self.new}, scope: {self.scope}>'
