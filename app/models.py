from app import logger
from app.functions import hms_to_string, seconds_to_hms
from config import Config, local
from datetime import date, datetime, timedelta
from pynamodb.models import Model
from pynamodb.attributes import UnicodeAttribute, UTCDateTimeAttribute, NumberAttribute, MapAttribute, ListAttribute


class Step(MapAttribute):
    """Each Step is used as a list item underneath the Recipe class."""
    number = NumberAttribute()
    text = UnicodeAttribute()
    then_wait = NumberAttribute(null=True)
    then_wait_ui = UnicodeAttribute(null=True)
    note = UnicodeAttribute(null=True)
    when = UnicodeAttribute(null=True)

    def update_ui_fields(self):
        """Creates the _ui fields for date & time attributes, if they don't already exist."""
        if not self.then_wait_ui and self.then_wait:
            self.then_wait_ui = hms_to_string(seconds_to_hms(self.then_wait))

    def __init__(self, number=number, text=text, then_wait=then_wait, then_wait_ui=then_wait_ui, note=note,
                 when=when, **attrs):
        super().__init__(**attrs)
        self.number = number
        self.text = text
        self.then_wait = then_wait
        self.then_wait_ui = then_wait_ui
        self.note = note
        self.when = when

        self.update_ui_fields()

    def __repr__(self):
        return f'<Step #{self.number}, then_wait: {self.then_wait}>'


class Recipe(Model):
    class Meta:
        table_name = 'Recipe'
        region = Config.aws_region
        if local:  # Use the local DynamoDB instance when running locally
            host = 'http://localhost:8008'

    # Primary recipe attributes
    id = UnicodeAttribute(hash_key=True)
    name = UnicodeAttribute()
    author = UnicodeAttribute()
    source = UnicodeAttribute()
    difficulty = UnicodeAttribute()

    # TODO: Figure out class-based validation that works with NumberAttribute()
    #  length = property(operator.attrgetter('_length'))
    #  @length.setter
    #  def length(self, l):
    #     if l < 0:
    #         raise ValueError("Length must be greater than zero.")
    #     self._length = l
    length = NumberAttribute(default=0)

    # Steps is an embedded list of dictionaries ("maps")
    steps = ListAttribute(of=Step)

    # Dates & times
    now = datetime.utcnow()
    date_added = UTCDateTimeAttribute(default=now)
    date_added_ui = UnicodeAttribute(default=now.strftime(Config.date_format))
    # TODO: Ensure date_added always remains a datetime() -- not a date() object

    start_time = UTCDateTimeAttribute(default=now)
    start_time_ui = UnicodeAttribute(default=now.strftime(Config.datetime_format))

    finish_time = UTCDateTimeAttribute(null=True)
    finish_time_ui = UnicodeAttribute(null=True)

    total_time_ui = UnicodeAttribute(null=True)

    def adjust_start_time(self, seconds):
        """Adjust the starting timestamp by a specified number of seconds."""
        self.start_time = self.start_time + timedelta(seconds=seconds)

        # Finish timestamp is dynamic based on start time & length
        self.finish_time = self.start_time + timedelta(seconds=self.length)

    def adjust_timezone(self, hours):
        """Adjust all timestamps by a specified number of hours."""
        self.date_added = self.date_added + timedelta(seconds=3600 * hours)
        self.start_time = self.start_time + timedelta(seconds=3600 * hours)
        self.finish_time = self.finish_time + timedelta(seconds=3600 * hours)

    def update_length(self, save=True):
        """Update the recipe's length (in seconds) by summing the length of each step."""
        logger.debug(f"Start of Recipe.update_length() for {self.name}")
        if not self.steps:  # if steps is an empty list
            self.length = 0
            return

        original_length = self.length or -1
        length = 0

        for step in self.steps:
            if isinstance(step.then_wait, timedelta):
                length += int(step.then_wait.total_seconds())  # wrapping w/int() because total_seconds() returns float
            else:
                length += step.then_wait

        logger.debug(f"Calculated length: {length}, original length: {original_length}")
        self.length = length

        if length != original_length and save:
            # Update the database if the length changed
            self.save()
            logger.info(f"Updated recipe {self.name} to reflect its new length: {self.length}.")

        logger.debug("End of Recipe.update_length()")

    def update_ui_fields(self):
        """Creates the _ui fields for date & time attributes, if they don't already exist."""
        data_changed = False

        if not self.date_added_ui and self.date_added:
            self.date_added_ui = self.date_added.strftime(Config.date_format)
            logger.debug(f"date_added_ui changed for recipe {self.name}")
            data_changed = True

        if not self.start_time_ui and self.start_time:
            self.start_time_ui = self.start_time.strftime(Config.datetime_format)
            logger.debug(f"start_time_ui changed for recipe {self.name}")
            data_changed = True

        if not self.finish_time_ui and self.finish_time:
            self.finish_time_ui = self.finish_time.strftime(Config.datetime_format)
            logger.debug(f"finish_time_ui changed for recipe {self.name}")
            data_changed = True

        if not self.total_time_ui and self.length:
            self.total_time_ui = hms_to_string(seconds_to_hms(self.length))
            logger.debug(f"total_time_ui changed for recipe {self.name}")
            data_changed = True

        # Update the db if any data was changed
        if data_changed:
            logger.debug(f"Data changed for recipe {self.name}")
            # logger.debug(f"About to update the db...")
            self.save()
            logger.debug(f"...db updated!")
            pass

    def __init__(self, id=id, name=name, author=author, source=source, difficulty=difficulty, length=length,
                 steps=steps, date_added=date_added, start_time=start_time, finish_time=finish_time,
                 date_added_ui=date_added_ui, start_time_ui=start_time_ui, finish_time_ui=finish_time_ui,
                 total_time_ui=total_time_ui, **attrs):
        super().__init__(**attrs)

        self.id = id
        self.name = name
        self.author = author
        self.source = source
        self.difficulty = difficulty

        self.length = length or 0
        self.steps = steps or []

        self.date_added = date_added or date.today()
        self.date_added_ui = date_added_ui

        self.start_time = start_time or datetime.utcnow()
        self.start_time_ui = start_time_ui

        self.finish_time = finish_time
        self.finish_time_ui = finish_time_ui
        if not finish_time_ui and self.finish_time is not None:
            self.finish_time_ui = self.finish_time.strftime(Config.datetime_format)

        self.total_time_ui = total_time_ui
        if not self.total_time_ui and self.length:
            self.total_time_ui = hms_to_string(seconds_to_hms(self.length))

        # Update the UI fields when initialized, if necessary
        # TODO: Set to the browser's timezone automatically instead of forcing PST
        # self.adjust_timezone(-7)
        # self.update_ui_fields()

    def __repr__(self):
        return f'<Recipe {self.id}: {self.name}>'


class Replacement(Model):
    class Meta:
        table_name = 'Replacement'
        region = Config.aws_region
        if local:  # Use the local DynamoDB instance when running locally
            host = 'http://localhost:8008'

    scope = UnicodeAttribute(hash_key=True)
    old = UnicodeAttribute(range_key=True)
    new = UnicodeAttribute()

    def __init__(self, scope=scope, old=old, new=new, **attrs):
        super().__init__(**attrs)
        self.scope = scope
        self.old = old
        self.new = new

    def __repr__(self):
        return f'<Replacement Text | scope: {self.scope}, old: {self.old}, new: {self.new}>'
