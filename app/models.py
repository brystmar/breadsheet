from datetime import date, datetime, timedelta
from pynamodb.models import Model
from pynamodb.attributes import UnicodeAttribute, UTCDateTimeAttribute, NumberAttribute, MapAttribute, ListAttribute


class Step(MapAttribute):
    number = NumberAttribute(default=0)
    text = UnicodeAttribute()
    then_wait = NumberAttribute(default=0)
    note = UnicodeAttribute()

    def __repr__(self):
        return f'<Step #{self.number}, then_wait: {self.then_wait}>'


class Recipe(Model):
    class Meta:
        table_name = 'Recipe'

    id = UnicodeAttribute(hash_key=True)
    name = UnicodeAttribute()
    author = UnicodeAttribute()
    source = UnicodeAttribute()
    difficulty = UnicodeAttribute()
    date_added = UTCDateTimeAttribute(default=date.today())
    steps = ListAttribute(of=Step)
    length = NumberAttribute(default=0)

    # TODO: Make these lines unnecessary!
    # force PST
    start_time = UTCDateTimeAttribute(default=datetime.utcnow() - timedelta(seconds=3600 * 7))
    start_time_ui = UnicodeAttribute(default=(datetime.utcnow() - timedelta(seconds=3600 * 7)).strftime('%Y-%m-%d %H:%M:%S'))

    def __repr__(self):
        return f'<Recipe {id}: {self.name}>'


class Replacement(Model):
    class Meta:
        table_name = 'Replacement'

    scope = UnicodeAttribute(hash_key=True)
    old = UnicodeAttribute(range_key=True)
    new = UnicodeAttribute()

    def __repr__(self):
        return f'<Replacement Text old: {self.old}, new: {self.new}, scope: {self.scope}>'
