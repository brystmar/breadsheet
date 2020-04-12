from backend.global_logger import logger
from backend.config import Config, local
from backend.functions import generate_new_id
from datetime import datetime, timedelta
from pynamodb.models import Model
from pynamodb.attributes import UnicodeAttribute, UTCDateTimeAttribute, NumberAttribute, \
    MapAttribute, ListAttribute, BooleanAttribute
import json


class Step(MapAttribute):
    """Individual step within a Recipe class.  Recipe.steps is a list of Step classes."""
    step_id = UnicodeAttribute()

    # Step number
    number = NumberAttribute()

    # Brief summary of the step's directions
    text = UnicodeAttribute()

    # How long to wait after finishing this step? Essentially the step's length.
    then_wait = NumberAttribute(default=0)

    # Longer notes field
    note = UnicodeAttribute(null=True)

    def to_dict(self) -> dict:
        return {
            "step_id":   self.step_id.__str__(),
            "number":    int(self.number),
            "text":      self.text.__str__(),
            "then_wait": int(self.then_wait),
            "note":      self.note.__str__() if self.note else None
        }

    def to_json(self) -> str:
        """Converts output from the to_dict() method to a JSON-serialized string."""
        return json.dumps(self.to_dict(), ensure_ascii=True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Null handling for step_id is a little different until the Prod db is updated
        # TODO: Remove once the Prod db is updated
        if 'step_id' not in kwargs.keys() or kwargs['step_id'] is None:
            self.step_id = generate_new_id(short=True)
            # logger.debug(f"Generated new step_id: {self.step_id}")

    def __repr__(self) -> str:
        return f'<Step #{self.number}, id: {self.step_id}, then_wait: {self.then_wait}>'


class Recipe(Model):
    class Meta:
        table_name = 'Recipe'
        region = Config.AWS_REGION
        if local:  # Use the local DynamoDB instance when running locally
            host = 'http://localhost:8008'

    ## Primary attributes ##
    id = UnicodeAttribute(hash_key=True, default=generate_new_id(short=True))

    # Title of the recipe
    name = UnicodeAttribute()

    # Author & source (`str`), both optional
    author = UnicodeAttribute(null=True)
    source = UnicodeAttribute(null=True)

    # Difficulty (`str`): Beginner, Intermediate, Advanced, or Expert
    difficulty = UnicodeAttribute(default="Beginner")

    # Determines how the UI calculates the timing for this recipe
    solve_for_start = BooleanAttribute(default=True)

    # Length (`int`): measured in seconds
    length = NumberAttribute(default=0)
    # TODO: Figure out class-based validation that works with NumberAttribute()
    #  length = property(operator.attrgetter('_length'))
    #  @length.setter
    #  def length(self, l):
    #     if l < 0:
    #         raise ValueError("Length must be greater than zero.")
    #     self._length = l

    # Steps (`list`): a list of dictionaries / "maps"
    steps = ListAttribute(of=Step)

    ## Datetime attributes ##
    # Each is stored as a UTC timestamp
    # TODO: Change the db values to epoch
    # TODO: Convert epoch to/from datetime in the Recipe model
    date_added = UTCDateTimeAttribute(default=datetime.utcnow())
    start_time = UTCDateTimeAttribute(default=date_added)

    def update_length(self, save=True):
        """Update the recipe's length (in seconds) by summing the length of each step."""
        logger.debug(f"Start of Recipe.update_length() for {self}")

        # Null handling
        if not self.steps:
            if self.length != 0:
                self.length = 0
                logger.debug(f"Updating Recipe")
                self.save()
                logger.info(f"Updated recipe {self.name} to reflect its new length: {self.length}.")
                return

            self.length = 0
            return

        original_length = self.length or -1
        length = 0

        for step in self.steps:
            if isinstance(step['then_wait'], timedelta):
                # Wrapping w/int() since timedelta.total_seconds() returns float
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
        """Convert this recipe (including any steps) to a python dictionary."""
        step_list = []
        if self.steps:
            for step in self.steps:
                step_list.append(step.to_dict())

        return {
            "id":              self.id.__str__(),
            "name":            self.name.__str__(),
            "author":          self.author.__str__() if self.author else None,
            "source":          self.source.__str__() if self.source else None,
            "difficulty":      self.difficulty.__str__(),
            "solve_for_start": self.solve_for_start if self.solve_for_start else True,
            "length":          int(self.length),
            "date_added":      self.date_added.__str__(),
            "start_time":      self.start_time.__str__(),
            "steps":           step_list
        }

    def to_json(self) -> str:
        """Convert output from the to_dict() method to a JSON-serialized string."""
        return json.dumps(self.to_dict(), ensure_ascii=True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Don't rely on the provided value for recipe length
        self.update_length()

    def __repr__(self) -> str:
        return f'<Recipe | id: {self.id}, name: {self.name}, length: {self.length}, ' \
               f'steps: {len(self.steps)}>'


class Replacement(Model):
    class Meta:
        table_name = 'Replacement'
        region = Config.AWS_REGION
        if local:  # Use the local DynamoDB instance when running locally
            host = 'http://localhost:8008'

    scope = UnicodeAttribute(hash_key=True)
    old = UnicodeAttribute(range_key=True)
    new = UnicodeAttribute()

    def to_dict(self) -> dict:
        return {
            "scope": self.scope.__str__(),
            "old":   self.old.__str__(),
            "new":   self.new.__str__()
        }

    def to_json(self) -> str:
        """Converts output from the to_dict() method to a JSON-serialized string."""
        return json.dumps(self.to_dict(), ensure_ascii=True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def __repr__(self) -> str:
        return f'<Replacement Text | scope: {self.scope}, old: {self.old}, new: {self.new}>'
