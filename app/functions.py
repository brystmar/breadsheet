from app import db, logger
from app.main.forms import ThenWaitForm, StartFinishForm
from app.models import Recipe, Step, Replacement
from datetime import datetime, timedelta


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


def convert_recipe_strings_to_datetime(recipe_input) -> Recipe:
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


def calculate_recipe_length(recipe_input):
    """Add/update the recipe_input's length (in seconds) by summing the length of each step."""
    logger.debug(f"Start of calculate_recipe_length() for recipe_input {recipe_input.id}")
    try:
        original_length = recipe_input.length
    except KeyError:
        original_length = -1

    length = 0
    for step in recipe_input.steps:
        if isinstance(step.then_wait, timedelta):
            length += int(step.then_wait.total_seconds())  # total_seconds returns a float
        else:
            length += step.then_wait

    logger.debug(f"Calculated length: {length}, original length: {original_length}")
    recipe_input.length = length

    if length != original_length:
        # Update the database if the length changed
        write_response = db.Table("Recipe").put_item(Item=cleanup_before_db_write(recipe_input))

        # Check the response code
        response_code = write_response['ResponseMetadata']['HTTPStatusCode']
        if response_code == 200:
            logger.info("Recipe successfully added to the db.")
        else:
            logger.warning(f"DynamoDB error: HTTPStatusCode={response_code}")
            logger.debug(f"Full response log:\n{write_response['ResponseMetadata']}")

        logger.info(f"Updated recipe_input {recipe_input.id} in the database to reflect its new length.")

    logger.debug("End of calculate_recipe_length()")
    return recipe_input


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


def set_when(steps, when) -> Recipe.steps:
    """Calculate when each step should begin, using a list of steps plus the benchmark time. Returns a list of steps."""

    logger.debug(f"Start of set_when(), with when={when}, {len(steps)} steps, all steps: {steps}")
    i = 0
    for step in steps:
        logger.debug(f"Looking at step {step.number}, when={when.strftime('%a %H:%M')},"
                     f"then_wait={step.then_wait}")

        # Set the 'when' for this step
        step.when = when.strftime('%a %H:%M')

        # Create a timedelta object for then_wait to simplify formulas
        step.then_wait = 0 if step.then_wait is None else int(step.then_wait)
        step.then_wait_timedelta = timedelta(seconds=step.then_wait)

        # Increment
        when += step.then_wait_timedelta

        step.then_wait_ui = str(step.then_wait_timedelta)
        step.then_wait_list = step.then_wait_ui.split(":")
        i += 1

        logger.debug(f"Finished step {step.number}")

    logger.debug(f"End of set_when(), returning: {steps}")
    return steps


def add_recipe_ui_fields(recipe_input) -> Recipe:
    """Input: an individual Recipe class.  Populates date_added_ui, start_time, finish_time, & total_time_ui."""
    logger.debug(f"Start of add_recipe_ui_fields() for {recipe_input.id}: {recipe_input.name}")

    recipe_input.date_added_ui = str(recipe_input.date_added)[:10]

    # Ensure start_time is a timedelta object
    if not isinstance(recipe_input.start_time, datetime):
        recipe_input.start_time = datetime.strptime(recipe_input.start_time, Config.datetime_format)

    if recipe_input.length in (None, 0):
        recipe_input.finish_time = recipe_input.start_time
        recipe_input.finish_time_ui = recipe_input.start_time_ui
        recipe_input.length = 0
    else:
        delta_length = timedelta(seconds=int(recipe_input.length))
        recipe_input.finish_time = recipe_input.start_time + delta_length
        recipe_input.finish_time_ui = recipe_input.finish_time.strftime(Config.datetime_format)

        if 'day' in str(delta_length):
            # If the recipe_input takes >24hrs, the system formats the string: '2 days, 1:30:05'
            delta_length_split = str(delta_length).split(", ")
            delta_to_parse = delta_length_split[1].split(':')
            recipe_input.total_time_ui = f"{delta_length_split[0]}, {hms_to_string(delta_to_parse)}"
        else:
            recipe_input.total_time_ui = hms_to_string(str(delta_length).split(':'))

    logger.debug(f"End of add_recipe_ui_fields()")
    return recipe_input


def create_tw_forms(steps) -> list:
    """Create a form for the 'then wait...' display for recipe steps, then populate it with data."""
    logger.debug(f"Start of create_tw_forms(), with: {steps}")

    twforms = []
    for step in steps:
        logger.debug(f"Looking at step {step.number}, then_wait={step.then_wait}, then_wait_ui={step.then_wait_ui}")
        tw = ThenWaitForm()
        tw.step_number = step.number

        # If steps take >24hrs, timedelta strings are formatted: '2 days, 1:35:28'
        if 'day' in step.then_wait_ui:
            # Split the string into days, then everything else
            days = int(step.then_wait_ui.split(" day")[0])
            # days = days // (60 * 60 * 24)

            # Split the second portion by ':', then add the number of hours
            hours = int(step.then_wait_list[1]) + (days * 24)
            tw.then_wait_m.data = step.then_wait_list[2]
        else:
            # Otherwise, just split as normal
            hours = step.then_wait_list[0]
            tw.then_wait_m.data = step.then_wait_list[1]

        # timedelta doesn't zero-pad the hours, so F* IT! WE'LL DO IT LIVE!
        if int(hours) <= 9:
            tw.then_wait_h.data = "0" + str(hours)
        else:
            tw.then_wait_h.data = str(hours)

        tw.then_wait = step.then_wait
        logger.debug(f"Done w/{step.number}: then_wait_h={tw.then_wait_h.data}, then_wait_m={tw.then_wait_m.data}")
        twforms.append(tw)
    logger.debug(f"End of create_tw_forms(), returning {twforms}")
    return twforms


def create_start_finish_forms(recipe_input) -> StartFinishForm:
    """Set values for the form displaying start & finish times for this recipe."""
    logger.debug(f"Start of create_start_finish_forms(), for {recipe_input.id}")

    seform = StartFinishForm()
    seform.recipe_id.data = recipe_input.id
    seform.start_date.data = recipe_input.start_time
    seform.start_time.data = recipe_input.start_time
    seform.finish_date.data = recipe_input.finish_time
    seform.finish_time.data = recipe_input.finish_time
    seform.solve_for_start.data = "1"

    logger.debug(f"End of create_start_finish_forms(), returning seform: {seform}")
    return seform
