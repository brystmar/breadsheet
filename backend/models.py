from backend.global_logger import logger
from backend.config import Config, local
from backend.functions import generate_new_id
from datetime import datetime, timedelta
from pynamodb.models import Model
from pynamodb.attributes import UnicodeAttribute, UTCDateTimeAttribute, NumberAttribute, \
    MapAttribute, ListAttribute, BooleanAttribute


class Step(MapAttribute):
    """
    Individual step within a Recipe class.
    Recipe.steps is a list of Step classes.
    """
    step_id = UnicodeAttribute(default=generate_new_id(short=True))

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

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

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
    url = UnicodeAttribute(null=True)

    # Difficulty (`str`): Beginner, Intermediate, Advanced, or Expert
    difficulty = UnicodeAttribute(default="Beginner")

    # Determines how the UI calculates the timing for this recipe
    solve_for_start = BooleanAttribute(default=True)

    # Length (`int`): measured in seconds
    length = NumberAttribute(default=0)

    # Steps (`list`): a list of dictionaries / "maps"
    steps = ListAttribute(of=Step, default=[], null=True)

    ## Datetime attributes ##
    # Stored as UTC timestamp in the db, operates as datetime here, exported as string or epoch
    date_added = UTCDateTimeAttribute(default=datetime.utcnow())
    start_time = UTCDateTimeAttribute(default=datetime.utcnow())
    last_modified = UTCDateTimeAttribute(default=datetime.utcnow(), null=True)

    def update_last_modified(self):
        self.last_modified = datetime.utcnow()

    def update_length(self, save=True):
        """Update the recipe's length (in seconds) by summing the length of each step."""
        # logger.debug(f"Start of Recipe.update_length() for {self}")

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

        # logger.debug(f"Calculated length: {length}, original length: {original_length}")
        self.length = length

        if length != original_length:
            # Always update last_modified
            logger.debug(f"Updating last_modified (was {self.last_modified}).")
            self.last_modified = datetime.utcnow()
            if save:
                # User specifies if they want changes to be saved to the db
                logger.debug(f"Attempting to save {self.__repr__()}")
                self.save()
                logger.info(f"Updated recipe {self.name} to reflect its new length: {self.length}.")

        # logger.debug("End of Recipe.update_length()")

    def to_dict(self, dates_as_epoch=False) -> dict:
        """
        Convert this recipe (including any steps) to a python dictionary.
        Returns dates in ISO format (default), or as a JavaScript-friendly epoch.
        """
        step_list = []
        if self.steps:
            for step in self.steps:
                if isinstance(step, dict):
                    # logger.debug(f"Step: {step}, type: {type(step)}")
                    step_list.append(step)
                elif isinstance(step, Step):
                    step_list.append(step.to_dict())
                else:
                    raise TypeError(f"Invalid type for provided step: {step} (type {type(step)})")

        # logger.debug(f"to_dict start_time: {self.start_time}, type: {type(self.start_time)}")

        output = {
            "id":              self.id.__str__(),
            "name":            self.name.__str__(),
            "author":          self.author.__str__() if self.author else None,
            "source":          self.source.__str__() if self.source else None,
            "url":             self.url.__str__() if self.url else None,
            "difficulty":      self.difficulty.__str__(),
            "solve_for_start": self.solve_for_start,
            "length":          int(self.length),
            "date_added":      self.date_added.timestamp() * 1000,  # JS timestamps are in ms
            "start_time":      self.start_time.timestamp() * 1000,
            "last_modified":   self.last_modified.timestamp() * 1000,
            "steps":           step_list
        }

        if not dates_as_epoch:
            output['date_added'] = self.date_added.isoformat()
            output['start_time'] = self.start_time.isoformat()
            output['last_modified'] = self.last_modified.isoformat()

        return output

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Generate a unique id if the recipe doesn't have one yet
        if 'id' not in kwargs:
            self.id = generate_new_id(short=True)

        # Validate URLs
        if 'url' in kwargs:
            if kwargs['url'] is None or kwargs['url'][:4] != 'http' or '://' not in kwargs['url']:
                logger.debug(f"Invalid input for URL: {kwargs['url']}")
                self.url = ""

        # Convert any provided epoch dates/times to datetime
        if 'date_added' in kwargs:
            if not kwargs['date_added'] or kwargs['date_added'].__str__().lower() in \
                    ("none", "null", "nan"):
                self.date_added = datetime.utcnow()
            else:
                if isinstance(self.date_added, (int, float)):
                    # Convert from JS milliseconds to seconds
                    self.date_added = datetime.utcfromtimestamp(kwargs['date_added'] / 1000)

        if 'start_time' in kwargs:
            if not kwargs['start_time'] or kwargs['start_time'].__str__().lower() in \
                    ("none", "null", "nan"):
                self.start_time = self.date_added
            else:
                if isinstance(self.start_time, (int, float)):
                    # Convert from JS milliseconds to seconds
                    self.start_time = datetime.utcfromtimestamp(kwargs['start_time'] / 1000)

        if 'last_modified' in kwargs:
            if not kwargs['last_modified'] or kwargs['last_modified'].__str__().lower() in \
                    ("none", "null", "nan"):
                self.last_modified = self.date_added
            else:
                if isinstance(self.last_modified, (int, float)):
                    # Convert from JS milliseconds to seconds
                    self.last_modified = datetime.utcfromtimestamp(kwargs['last_modified'] / 1000)

    def __setattr__(self, name, value):
        """Apply validation when values are changed."""
        # URL format validation
        if name.lower() == "url":
            if value not in ("", None):
                if value[:4] != "http" or "://" not in value:
                    raise ValueError("Invalid URL format.")

        # TODO: Troubleshoot this logic
        # Update length when modifying steps
        # if name.lower() == "steps":
        #     super().__setattr__(name, value)
        #     self.update_length(save=True)

        # Calculate the length instead of accepting a new value for length
        # if name.lower() == "length" and self.length != value:
        #     self.update_length(save=True)

        super().__setattr__(name, value)

    def __repr__(self) -> str:
        return f'<Recipe | id: {self.id}, name: {self.name}, length: {self.length}, ' \
               f'steps: {len(self.steps) if self.steps else 0}>'


class Replacement(Model):
    class Meta:
        table_name = 'Replacement'
        region = Config.AWS_REGION
        if local:  # Use the local DynamoDB instance when running locally
            host = 'http://localhost:8008'

    # TODO: Add an id attribute to simplify identifying each record
    #  id = UnicodeAttribute()  <-- shouldn't this be the primary key?
    scope = UnicodeAttribute(hash_key=True)
    old = UnicodeAttribute(range_key=True)
    new = UnicodeAttribute()

    def to_dict(self) -> dict:
        return {
            "scope": self.scope.__str__(),
            "old":   self.old.__str__(),
            "new":   self.new.__str__()
        }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def __getitem__(self, scope):
        try:
            return self.scope
        except TypeError as e:
            logger.error(f"Unsupported __getitem__ request: {e}")
            raise e

    def __repr__(self) -> str:
        return f'<Replacement Text | scope: {self.scope}, old: {self.old}, new: {self.new}>'
