from backend.global_logger import logger
from backend.config import Config, local
from backend.functions import generate_new_id
from datetime import datetime, timedelta
from pynamodb.models import Model
from pynamodb.attributes import UnicodeAttribute, UTCDateTimeAttribute, NumberAttribute, \
    MapAttribute, ListAttribute, BooleanAttribute, Attribute
import json
import shortuuid


class Step(MapAttribute):
    """Individual step under a Recipe class.  Recipe.steps is a list of Step classes."""
    step_id = UnicodeAttribute()

    # Step number
    number = NumberAttribute()

    # Brief summary of the step's directions
    text = UnicodeAttribute()

    # How long to wait after finishing this step?
    # Similar to length, but more descriptive for a Step object
    then_wait = NumberAttribute(default=0)

    # Longer notes field
    note = UnicodeAttribute(null=True)

    def to_dict(self) -> dict:
        return {
            "step_id":   self.step_id.__str__(),
            "number":    int(self.number),
            "text":      self.text.__str__(),
            "then_wait": int(self.then_wait),
            "note":      self.note.__str__()
        }

    def to_json(self) -> str:
        """Converts output from the to_dict() method to a JSON-serialized string."""
        return json.dumps(self.to_dict(), ensure_ascii=True)

    def _null_handler(self, attr):
        """
        Nulls in the ORM should be represented as a NoneType object instead of:
          <pynamodb.attributes.UnicodeAttribute object at 0x7f9e104d4c18>
        """
        # logger.debug(f"Starting Step._null_handler w/{type(attr)}")
        if isinstance(attr, UnicodeAttribute):
            if attr.null:
                return None
        elif isinstance(attr, NumberAttribute):
            if attr.null:
                return 0
        elif isinstance(attr, ListAttribute):
            if attr.null:
                return []
        elif isinstance(attr, UTCDateTimeAttribute):
            if attr.null:
                return datetime.now()
        elif isinstance(attr, BooleanAttribute):
            if attr.null:
                return True

        # logger.debug("No matches, returning the attribute untouched.")
        return attr

    def __init__(self, step_id=step_id, number=number, text=text, then_wait=then_wait,
                 note=note, **attrs):
        super().__init__(**attrs)

        # Null handling for step_id is a little different until the Prod db is updated
        if isinstance(step_id, UnicodeAttribute):
            step_id = shortuuid.uuid()

        self.step_id = step_id
        self.number = self._null_handler(number)
        self.text = self._null_handler(text)
        self.then_wait = self._null_handler(then_wait)
        self.note = self._null_handler(note)

    def __repr__(self) -> str:
        return f'<Step #{self.number}, id: {self.step_id}, then_wait: {self.then_wait}>'


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

    # Determines how the UI calculates the timing for this recipe
    solve_for_start = BooleanAttribute(default=True)

    # Length is measured in whole seconds
    length = NumberAttribute(default=0)
    # TODO: Figure out class-based validation that works with NumberAttribute()
    #  length = property(operator.attrgetter('_length'))
    #  @length.setter
    #  def length(self, l):
    #     if l < 0:
    #         raise ValueError("Length must be greater than zero.")
    #     self._length = l

    # Steps is an embedded list of dictionaries ("maps")
    steps = ListAttribute(of=Step)

    ## Datetime attributes ##
    # Each is stored as a UTC timestamp, no time zone
    date_added = UTCDateTimeAttribute()
    start_time = UTCDateTimeAttribute()

    def adjust_start_time(self, seconds):
        """Adjust the starting timestamp by a specified number of seconds."""
        self.start_time = self.start_time + timedelta(seconds=seconds)

    def update_length(self, save=True):
        """Update the recipe's length (in seconds) by summing the length of each step."""
        logger.debug(f"Start of Recipe.update_length() for {self}")
        if not self.steps:  # if steps is an empty list
            self.length = 0
            return

        original_length = self.length or -1
        length = 0

        for step in self.steps:
            if isinstance(step['then_wait'], timedelta):
                # Wrapping w/int() because total_seconds() [a timedelta method] returns float
                length += int(step['then_wait'].total_seconds())
            else:
                length += step['then_wait']

        logger.debug(f"Calculated length: {length}, original length: {original_length}")
        self.length = length

        if length != original_length and save:
            # Update the database if the length changed
            logger.debug(f"Attempting to save Recipe...")
            self.save()
            logger.info(f"Updated recipe {self.name} to reflect its new length: {self.length}.")

        logger.debug("End of Recipe.update_length()")

    def to_dict(self) -> dict:
        """Converts this recipe (including any steps) to a python dictionary."""
        step_list = []
        if self.steps:
            for step in self.steps:
                step_list.append(step.to_dict())

        output = {
            "id":              self.id.__str__(),
            "name":            self.name.__str__(),
            "author":          self.author.__str__(),
            "source":          self.source.__str__(),
            "difficulty":      self.difficulty.__str__(),
            "solve_for_start": self.solve_for_start.__str__(),
            "length":          int(self.length),
            "date_added":      self.date_added.__str__(),
            "start_time":      self.start_time.__str__(),
            "steps":           step_list
        }

        logger.debug("Finished to_dict()")
        return output

    def to_json(self) -> str:
        """Converts output from the to_dict() method to a JSON-serialized string."""
        return json.dumps(self.to_dict(), ensure_ascii=True)

    def __init__(self, id=id, name=name, author=author, source=source, difficulty=difficulty,
                 solve_for_start=solve_for_start, length=length, steps=steps,
                 date_added=date_added, start_time=start_time, **attrs):
        """Update the UI fields when initialized, as necessary."""
        super().__init__(**attrs)

        self.id = id or generate_new_id()
        self.name = name
        self.author = self._null_handler(author)
        self.source = self._null_handler(source)
        self.difficulty = difficulty
        self.solve_for_start = solve_for_start or True

        self.length = self._null_handler(length)
        self.steps = self._null_handler(steps)

        self.date_added = self._null_handler(date_added)
        self.start_time = self._null_handler(start_time)

        # Don't rely on the provided value for recipe length
        self.update_length()

    def _null_handler(self, attr):
        """
        Nulls in the ORM should be represented as a NoneType object instead of:
          <pynamodb.attributes.UnicodeAttribute object at 0x7f9e104d4c18>
        """
        # logger.debug(f"Starting Recipe._null_handler w/{type(attr)}")
        if isinstance(attr, UnicodeAttribute):
            if attr.null:
                return None
        elif isinstance(attr, NumberAttribute):
            if attr.null:
                return 0
        elif isinstance(attr, ListAttribute):
            if attr.null:
                return []
        elif isinstance(attr, UTCDateTimeAttribute):
            if attr.null:
                return datetime.now()
        elif isinstance(attr, BooleanAttribute):
            if attr.null:
                return True

        # logger.debug("No matches, returning the attribute untouched.")
        return attr

    def __repr__(self) -> str:
        return f'<Recipe | id: {self.id}, name: {self.name}, length: {self.length}, ' \
               f'steps: {len(self.steps)}>'


class Replacement(Model):
    class Meta:
        table_name = 'Replacement'
        region = Config.aws_region
        if local:  # Use the local DynamoDB instance when running locally
            host = 'http://localhost:8008'

    scope = UnicodeAttribute(hash_key=True)
    old = UnicodeAttribute(range_key=True)
    new = UnicodeAttribute()

    def to_dict(self) -> dict:
        output = {
            "scope": self.scope.__str__(),
            "old":   self.old.__str__(),
            "new":   self.new.__str__()
        }

        return output

    def to_json(self) -> str:
        """Converts output from the to_dict() method to a JSON-serialized string."""
        return json.dumps(self.to_dict(), ensure_ascii=True)

    def __init__(self, scope=scope, old=old, new=new, **attrs):
        super().__init__(**attrs)
        self.scope = scope
        self.old = old
        self.new = new

    def __repr__(self) -> str:
        return f'<Replacement Text | scope: {self.scope}, old: {self.old}, new: {self.new}>'
