from config import Config
from datetime import date, datetime, timedelta
from pynamodb.models import Model
from pynamodb.attributes import UnicodeAttribute, UTCDateTimeAttribute, NumberAttribute, MapAttribute, ListAttribute


class Step(MapAttribute):
    number = NumberAttribute(default=0)
    text = UnicodeAttribute()
    then_wait = NumberAttribute(default=0)
    then_wait_ui = UnicodeAttribute()
    note = UnicodeAttribute()

    def __init__(self, number, text, then_wait, then_wait_ui, note, **attrs):
        super().__init__(**attrs)

        # Allows initialization of the class on a single line
        self.number = number
        self.text = text
        self.then_wait = then_wait
        self.then_wait_ui = then_wait_ui
        self.note = note

    def __repr__(self):
        return f'<Step #{self.number}, then_wait: {self.then_wait}>'


class Recipe(Model):
    class Meta:
        table_name = 'Recipe'
        region = 'us-west-2'

    # Primary recipe attributes
    id = UnicodeAttribute(hash_key=True)
    name = UnicodeAttribute()
    author = UnicodeAttribute()
    source = UnicodeAttribute()
    difficulty = UnicodeAttribute()
    steps = ListAttribute(of=Step)
    length = NumberAttribute(default=0)

    # Dates & times
    date_added = UTCDateTimeAttribute(default=date.today())
    date_added_ui = UTCDateTimeAttribute(default=date.today().strftime(Config.date_format))

    # TODO: Set to the browser's timezone automatically instead of forcing PST
    start_time = UTCDateTimeAttribute(default=datetime.utcnow() - timedelta(seconds=3600 * 7))
    start_time_ui = UnicodeAttribute(default=(datetime.utcnow() - timedelta(seconds=3600 * 7)).
                                     strftime(Config.datetime_format))

    finish_time = UTCDateTimeAttribute()
    finish_time_ui = UnicodeAttribute()

    total_time_ui = UnicodeAttribute()

    def __repr__(self):
        return f'<Recipe {self.id}: {self.name}>'


class Replacement(Model):
    class Meta:
        table_name = 'Replacement'
        region = 'us-west-2'

    scope = UnicodeAttribute(hash_key=True)
    old = UnicodeAttribute(range_key=True)
    new = UnicodeAttribute()

    def __repr__(self):
        return f'<Replacement Text | scope: {self.scope}, old: {self.old}, new: {self.new}>'
