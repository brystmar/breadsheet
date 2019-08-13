from app.functions import hms_to_string
from config import Config
from datetime import date, datetime, timedelta
from pynamodb.models import Model
from pynamodb.attributes import UnicodeAttribute, UTCDateTimeAttribute, NumberAttribute, MapAttribute, ListAttribute


class Step(MapAttribute):
    number = NumberAttribute()
    text = UnicodeAttribute()
    then_wait = NumberAttribute()
    then_wait_ui = UnicodeAttribute()
    note = UnicodeAttribute()

    def __init__(self, number=number, text=text, then_wait=then_wait, then_wait_ui=then_wait_ui, note=note, **attrs):
        super().__init__(**attrs)

        # Allows initialization of the class on a single line
        self.number = number or 0
        self.text = text
        self.then_wait = then_wait or 0
        self.then_wait_ui = then_wait_ui or hms_to_string([0, 0, self.then_wait])
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

    start_time = UTCDateTimeAttribute(default=datetime.utcnow())
    start_time_ui = UnicodeAttribute(default=datetime.utcnow().strftime(Config.datetime_format))

    finish_time = UTCDateTimeAttribute()
    finish_time_ui = UnicodeAttribute()

    total_time_ui = UnicodeAttribute()

    def __init__(self, id=id, name=name, author=author, source=source, difficulty=difficulty, steps=steps,
                 length=length, date_added=date_added, date_added_ui=date_added_ui, start_time=start_time,
                 start_time_ui=start_time_ui, finish_time_ui=finish_time_ui, total_time_ui=total_time_ui, **attrs):
        super().__init__(**attrs)

        self.id = id
        self.name = name
        self.author = author
        self.source = source
        self.difficulty = difficulty
        self.steps = steps
        self.length = length

        # TODO: Set to the browser's timezone automatically instead of forcing PST
        self.date_added = date_added - timedelta(seconds=3600 * 7)
        self.date_added_ui = date_added_ui or self.date_added.strftime(Config.date_format)

        self.start_time = start_time - timedelta(seconds=3600 * 7)
        self.start_time_ui = start_time_ui or self.start_time.strftime(Config.datetime_format)

        self.finish_time = self.start_time + timedelta(seconds=self.length)
        self.finish_time_ui = finish_time_ui or self.finish_time.strftime(Config.datetime_format)

        self.total_time_ui = total_time_ui or hms_to_string([0, 0, self.length])

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
