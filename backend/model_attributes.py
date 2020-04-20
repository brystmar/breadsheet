# Custom pynamodb attributes for specific use cases
from backend.global_logger import logger
from pynamodb.attributes import Attribute, NumberAttribute
from pynamodb.constants import NUMBER
from datetime import datetime
from numbers import Number


class HybridDateTime(NumberAttribute):
    """
    Stores data as a number, yet behaves like a datetime object in Python.

    https://pynamodb.readthedocs.io/en/latest/attributes.html
    """
    # DATETIME_FORMAT = '%Y-%m-%dT%H:%M:%S.%f%z'

    # Tells PynamoDB that the attribute is stored as a number in DynamoDB
    #   (DynamoDB only recognizes `string`, `number`, or `binary`)
    attr_type = NUMBER

    def serialize(self, value) -> Number:
        # Convert the python value (datetime) to the format we want stored in the database: a number
        logger.debug(f"hdt.serialize({value})")
        if not value:
            value = datetime.utcfromtimestamp(0)
        return datetime.timestamp(value)

    def deserialize(self, value) -> datetime:
        # Convert the database value (number) to the format we want to use in python: datetime
        logger.debug(f"hdt.de-serialize({value})")
        if not value:
            value = 0
        value = int(float(value))
        return datetime.utcfromtimestamp(value)
