from app import logger
from datetime import datetime


# def sort_list_of_dictionaries(unsorted_list, key_to_sort_by, reverse=False) -> list:
#     return sorted(unsorted_list, key=lambda k: k[key_to_sort_by], reverse=reverse)


def generate_new_id() -> str:
    """Primary key (id) is a 54-digit, underscore-delimited epoch timestamp plus a random UUID.

    Ex: 1560043140.471138_65f078f6-aea2-41e0-be37-a62e2d5d5474"""
    import uuid
    new_id = ""

    # For my sanity, ensure all ids are the same length.  Timestamps occasionally end in 0, which the system truncates.
    while len(new_id) != 54:
        new_id = f"{datetime.utcnow().timestamp()}_{uuid.uuid4()}"

    return new_id


def hms_to_seconds(hms) -> int:
    """Convert a list of [hours, minutes, seconds] to a total number of seconds."""
    logger.debug(f"Start of hms_to_seconds(), with: {hms}")
    if not (isinstance(hms, list) and len(hms) == 3):
        logger.warning(f"Error in hms_to_seconds function: Invalid input {hms}.")
        logger.debug("End of hms_to_seconds(), returning 0")
        return 0

    if hms[0] is None:
        hms[0] = 0
    if hms[1] is None:
        hms[1] = 0
    if hms[2] is None:
        hms[2] = 0

    try:
        hms[0] = int(hms[0])
        hms[1] = int(hms[1])
        hms[2] = int(hms[2])
        result = (hms[0] * 60 * 60) + (hms[1] * 60) + (hms[2])

        logger.debug(f"End of hms_to_seconds(), returning: {result}")
        return result
    except TypeError:
        logger.warning(f"Error in hms_to_seconds function: List values {hms} cannot be converted to int.")
        logger.debug("End of hms_to_seconds(), returning 0")
        return 0


def hms_to_string(data) -> str:
    """Convert a list of [hrs, min, sec] to a human-readable string.  Yet again, because I'm a newbie."""
    logger.debug(f"Start of hms_to_string(), with: {data}")
    result = ''
    if data[0] in ('0', '00'):
        pass
    elif data[0] == '1':
        result = f'{data[0]} hr'
    else:
        result = f'{data[0]} hrs'

    if data[1] in ('0', '00') and result != '':
        logger.debug(f"End of hms_to_string(), returning: {result}")
        return result  # round off the seconds if it's an even number of hours
    elif data[1] in ('0', '00') and result == '':
        pass
    elif result == '':
        result += f'{data[1]} min'
    else:
        result += f', {data[1]} min'

    logger.debug(f"End of hms_to_string(), returning: {result}")
    return result


def cleanup_before_db_write(recipe_input):
    """Additional attributes are added to recipes & steps for easier local processing.  No need to add these to the db.

    Also, DynamoDB doesn't accept datetime objects in string fields, so we need to convert those fields to strings."""
    # logger.debug(f"Entering cleanup_before_db_write(), with: {recipe_input}")
    #
    # # Remove unnecessary attributes
    # recipe_fields_to_remove = ['start_time_ui', 'start_time_split', 'date_added_ui', 'total_time',
    #                            'finish_time', 'finish_time_ui']
    # step_fields_to_remove = ['when', 'then_wait_ui', 'then_wait_list', 'then_wait_timedelta']
    #
    # for r in recipe_fields_to_remove:
    #     result = recipe_input.pop(r, None)
    #
    #     if result is not None:
    #         # Only returns a non-null value if something was removed
    #         logger.debug(f"Removed recipe item: {r}")
    #
    # for step in recipe_input.steps:
    #     for s in step_fields_to_remove:
    #         result = step.pop(s, None)
    #
    #         if result is not None:
    #             logger.debug(f"Removed step #{step.number} item: {s}")
    #
    # # Convert datetime objects to strings
    # recipe_input.date_added = recipe_input.date_added.strftime(Config.date_format)
    # recipe_input.start_time = recipe_input.start_time.strftime(Config.datetime_format)
    #
    # logger.debug(f"End of cleanup_before_db_write(), with: {recipe_input}")
    return recipe_input


def convert_recipe_strings_to_datetime(recipe_input):
    """Most recipe fields are stored as strings in the db.  Convert them to datetime objects here."""
    # logger.debug(f"Start of convert_recipe_strings_to_datetime() for {recipe_input.id}: {recipe_input.name}")
    #
    # recipe_input.date_added = datetime.strptime(recipe_input.date_added, Config.date_format)
    #
    # # TODO: Make these lines unnecessary!
    # # force PST
    # recipe_input.start_time = datetime.utcnow() - timedelta(seconds=3600*7)
    # recipe_input.start_time_ui = recipe_input.start_time.strftime(Config.datetime_format)
    #
    # # Length comes in as type=Decimal; some functions only accept integers
    # try:
    #     recipe_input.length = int(recipe_input.length)
    # except KeyError:
    #     recipe_input.length = calculate_recipe_length(recipe_input)
    #
    # logger.debug(f"End of convert_recipe_strings_to_datetime()")
    return recipe_input
