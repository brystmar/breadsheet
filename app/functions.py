from app import logger
from datetime import datetime, timedelta
from numbers import Number


def generate_new_id() -> str:
    """Primary key (id) is a 17-digit epoch timestamp.  Ex: 1560043140.168794"""
    # For sanity, ensure all ids are the same length.  Timestamps occasionally end in 0, which the system truncates.
    new_id = ""
    while len(new_id) != 17:
        new_id = str(datetime.utcnow().timestamp())
    return new_id


def zero_pad(num) -> str:
    """Converts single-digit numbers to a 2-digit, zero-padded string"""
    try:
        # Convert to int in case we were passed a float, str, etc
        num = int(num)
    except (TypeError, ValueError):
        logger.warning(f"Input to zero_pad() must be convertible to int.")
        return num
    if 0 <= num <= 9:
        return f"0{num}"
    else:
        return str(num)


def seconds_to_hms(seconds_input) -> list:
    """Converts a raw number of seconds (int/float/str) to a list of strings: [days, hours, minutes, seconds]."""
    logger.debug(f"Start of seconds_to_hms(), with: {seconds_input} {type(seconds_input)}")
    try:
        data = int(seconds_input)
        if data < 0:
            logger.warning(f"seconds_to_hms() does not accept negative values.  Returning zeroes.")
            return ['0', '0', '00', '00']
        minutes, seconds = divmod(data, 60)
        hours, minutes = divmod(minutes, 60)
        days, hours = divmod(hours, 24)

        result = [str(days), str(hours), zero_pad(minutes), zero_pad(seconds)]
    except (ValueError, TypeError) as e:
        logger.warning(f"Input {seconds_input} {type(seconds_input)} to seconds_to_hms() cannot convert to int.")
        raise e
    logger.debug(f"End of seconds_to_hms(), returning: {result}")
    return result


def hms_to_seconds(hms) -> int:
    """Convert an int/str list of [days, hours, minutes, seconds] to a total number of seconds (int)."""
    try:
        result = int(timedelta(days=int(hms[0] or 0), hours=int(hms[1] or 0), minutes=int(hms[2] or 0),
                               seconds=int(hms[3] or 0)).total_seconds())
    except (ValueError, TypeError) as e:
        logger.warning(f"Input {hms} {type(hms)} to hms_to_seconds() cannot convert to int.")
        raise e
    return result


def hms_to_string(data) -> str:
    """Convert an int/str list of [days, hrs, min, sec] to a human-readable string.  Yet again, because I'm a newbie."""
    logger.debug(f"Start of hms_to_string(), with: {data}")

    # TODO: Add support for days
    # Days

    # Hours
    if data[0] in('0', '00', 0):
        result = ''
    elif data[0] in('1', 1):
        result = f'{data[0]} hr'
    else:
        result = f'{data[0]} hrs'

    # Minutes
    if data[1] in ('0', '00', 0) and result != '':
        logger.debug(f"End of hms_to_string(), returning: {result}")
        return result  # round off the seconds if it's an even number of hours
    elif data[1] in ('0', '00', 0) and result == '':
        pass
    elif result == '':
        result += f'{data[1]} min'
    else:
        result += f', {data[1]} min'

    # We don't care about seconds
    logger.debug(f"End of hms_to_string(), returning: {result}")
    return result
