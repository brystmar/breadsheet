from app import logger
from config import Config, local
from datetime import datetime, timedelta
from pynamodb.models import Model
from pynamodb.attributes import UnicodeAttribute, UTCDateTimeAttribute, NumberAttribute, MapAttribute, ListAttribute


class Step(MapAttribute):
    """Individual step under a Recipe class.  Recipe.steps is a list of Step classes."""
    # Step number
    number = NumberAttribute()

    # Brief summary of the step's directions
    text = UnicodeAttribute()

    # How long to wait after finishing this step?
    # Similar to length, but more descriptive for a Step object
    then_wait = NumberAttribute(null=True)

    # Longer notes field
    note = UnicodeAttribute(null=True)

    # When to begin this step?
    when = UnicodeAttribute(null=True)

    def __init__(self, number=number, text=text, then_wait=then_wait, note=note, when=when, **attrs):
        super().__init__(**attrs)

        self.number = number
        self.text = text
        self.then_wait = then_wait
        self.note = note
        self.when = when

    def __repr__(self):
        return f'<Step #{self.number}, then_wait: {self.then_wait}>'


class Recipe(Model):
    class Meta:
        table_name = 'Recipe'
        region = Config.aws_region
        if local:  # Use the local DynamoDB instance when running locally
            host = 'http://localhost:8008'

    ## Primary attributes ##
    # Unique identifier
    id = UnicodeAttribute(hash_key=True)

    # Title of the recipe
    name = UnicodeAttribute()

    # Author & source, if known
    author = UnicodeAttribute(null=True)
    source = UnicodeAttribute(null=True)

    # Difficulty is one of: Beginner, Intermediate, Advanced
    difficulty = UnicodeAttribute()

    # Length is measured in whole seconds
    length = NumberAttribute(default=0)
    # TODO: Figure out class-based validation that works with NumberAttribute()
    #  length = property(operator.attrgetter('_length'))
    #  @length.setter
    #  def length(self, l):
    #     if l < 0:
    #         raise ValueError("Length must be greater than zero.")
    #     self._length = l
    ""

    # Steps is an embedded list of dictionaries ("maps")
    steps = ListAttribute(of=Step)

    ## Datetime attributes ##
    # Each is stored as a UTC timestamp, no time zone
    date_added = UTCDateTimeAttribute()
    start_time = UTCDateTimeAttribute()
    finish_time = UTCDateTimeAttribute()

    def adjust_start_time(self, seconds):
        """Adjust the starting timestamp by a specified number of seconds."""
        self.start_time = self.start_time + timedelta(seconds=seconds)

        # Finish timestamp is dynamic based on start time & length
        self.finish_time = self.start_time + timedelta(seconds=self.length)

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

    def __init__(self, id=id, name=name, author=author, source=source, difficulty=difficulty, length=length,
                 steps=steps, date_added=date_added, start_time=start_time, **attrs):
        # Update the UI fields when initialized, if necessary
        super().__init__(**attrs)

        self.id = id
        self.name = name
        self.author = author
        self.source = source
        self.difficulty = difficulty

        self.length = length or 0
        self.steps = steps or []

        self.date_added = date_added or datetime.utcnow()
        self.start_time = self.date_added
        self.finish_time = self.date_added

    def __repr__(self):
        return f'<Recipe | id: {self.id}, name: {self.name}, added: {self.date_added}>'


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
