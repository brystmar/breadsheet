from app import logger
from app.functions import hms_to_string, seconds_to_hms
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

    when = UnicodeAttribute()
    then_wait_list = ListAttribute()

    def update_ui_fields(self):
        """Creates the _ui fields for date & time attributes, if they don't already exist."""
        if not self.then_wait_ui and self.then_wait:
            self.then_wait_ui = hms_to_string(seconds_to_hms(self.then_wait))

    def __init__(self, **attrs):
        super().__init__(**attrs)

        self.update_ui_fields()

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
    length = NumberAttribute(default=0)

    # Steps is an embedded list of dictionaries ("maps")
    steps = ListAttribute(of=Step)

    # Dates & times
    date_added = UTCDateTimeAttribute(default=date.today())
    date_added_ui = UnicodeAttribute(default=date.today().strftime(Config.date_format))

    start_time = UTCDateTimeAttribute(default=datetime.utcnow())
    start_time_ui = UnicodeAttribute(default=datetime.utcnow().strftime(Config.datetime_format))

    finish_time = UTCDateTimeAttribute()
    finish_time_ui = UnicodeAttribute()

    total_time_ui = UnicodeAttribute()

    def adjust_timezone(self, offset_hours):
        """Adjust the date & time fields based on a specified offset."""
        # TODO: Set to the browser's timezone automatically instead of forcing PST
        self.date_added = self.date_added + timedelta(seconds=3600 * offset_hours)
        self.start_time = self.start_time + timedelta(seconds=3600 * offset_hours)

        # Finish timestamp is dynamic based on start time & length
        self.finish_time = self.start_time + timedelta(seconds=self.length)

    def update_ui_fields(self):
        """Creates the _ui fields for date & time attributes, if they don't already exist."""
        data_changed = False
        if not self.date_added_ui and self.date_added:
            self.date_added_ui = self.date_added.strftime(Config.date_format)
            data_changed = True
            logger.debug(f"date_added_ui changed for recipe {self.name}")

        if not self.start_time_ui and self.start_time:
            self.start_time_ui = self.start_time.strftime(Config.datetime_format)
            data_changed = True
            logger.debug(f"start_time_ui changed for recipe {self.name}")

        if not self.finish_time_ui and self.finish_time:
            self.finish_time_ui = self.finish_time.strftime(Config.datetime_format)
            data_changed = True
            logger.debug(f"finish_time_ui changed for recipe {self.name}")

        if not self.total_time_ui and self.length:
            self.total_time_ui = hms_to_string(seconds_to_hms(self.length))
            data_changed = True
            logger.debug(f"total_time_ui changed for recipe {self.name}")

        # Update the db if any data was changed
        if data_changed:
            logger.debug(f"Data changed for recipe {self.name}")
            # logger.debug(f"About to update the db...")
            self.save()
            # logger.debug(f"...db updated!")
            pass

    def __init__(self, **attrs):
        super().__init__(**attrs)

        # Update the UI fields when initialized, if necessary
        self.adjust_timezone(-7)
        self.update_ui_fields()

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
