import re
from app import logger
from datetime import datetime, timedelta


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
    except (TypeError, ValueError) as e:
        raise e(f"Input {num} {type(num)} to zero_pad() must convert to int.")
    if 0 <= num <= 9:
        return f"0{num}"
    else:
        return str(num)


def seconds_to_hms(seconds_input) -> list:
    """Converts a raw number of seconds >=0 (int/float/str) to a list of strings: [days, hours, minutes, seconds]."""
    logger.debug(f"Start of seconds_to_hms(), with: {seconds_input} {type(seconds_input)}")
    try:
        data = int(seconds_input)
        if data < 0:
            logger.warning(f"seconds_to_hms() does not accept negative values.  Returning zeroes.")
            return ['0', '0', '00', '00']
        minutes, seconds = divmod(data, 60)
        hours, minutes = divmod(minutes, 60)
        days, hours = divmod(hours, 24)

        hms = [str(days), str(hours), zero_pad(minutes), zero_pad(seconds)]
    except (ValueError, TypeError) as e:
        raise e(f"Input {seconds_input} {type(seconds_input)} to seconds_to_hms() must convert to int.")
    logger.debug(f"End of seconds_to_hms(), returning: {hms}")
    return hms


def hms_to_seconds(hms) -> int:
    """Convert a tuple/list of int/float/str [days, hours, minutes, seconds] to a total number of seconds (int)."""
    # Ensure value is a list/tuple
    if not isinstance(hms, (list, tuple)):
        raise TypeError(f"Input {hms} {type(hms)} to hms_to_seconds() must be a 4-length list/tuple.")

    if len(hms) != 4:
        raise IndexError(f"Input {hms} {type(hms)} to hms_to_seconds() must be a 4-length list: [days, hrs, min, sec]")

    try:
        result = int(timedelta(days=int(hms[0] or 0), hours=int(hms[1] or 0), minutes=int(hms[2] or 0),
                               seconds=int(hms[3] or 0)).total_seconds())
    except (ValueError, TypeError) as e:
        raise e(f"Input values {hms} {type(hms)} to hms_to_seconds() must convert to int.")
    return result


def hms_to_string(data) -> str:
    """Converts days/hrs/min/sec to a human-readable string.

    Accepts any of these inputs:
    - A tuple/list of int/float/str [days, hrs, min, sec]
    - A timedelta object
    - A string formatted like the output of a timedelta object (Ex: '7:19:02' or '1 day, 7:19:02' or '2 days, 7:19:02')
    """
    logger.debug(f"Start of hms_to_string(), with: {data}, {type(data)}")

    if not isinstance(data, (list, tuple, timedelta, str)):
        raise TypeError(f"Input {data} {type(data)} to hms_to_string() must be str, timedelta, or 4-len list.")

    # For list/tuple, convert to timedelta to validate & standardize formatting for us
    if isinstance(data, (list, tuple)):
        # Must have 4 items in the list
        if len(data) != 4:
            raise IndexError(f"Input {data} {type(data)} to hms_to_string() must be "
                             f"a 4-length list: [days, hrs, min, sec]")

        try:
            data = timedelta(days=int(data[0] or 0), hours=int(data[1] or 0), minutes=int(data[2] or 0),
                             seconds=int(data[3] or 0))
        except (TypeError, ValueError) as e:
            raise e(f"Input {data} {type(data[0])} to hms_to_string() must convert to int.")

    # If input is timedelta, convert to string
    if isinstance(data, timedelta):
        # Inputs must be positive
        if data.total_seconds() < 0:
            raise ValueError(f"Input {data} {type(data)} to hms_to_string() must be positive.")
        data = str(data)

    # Input is a string
    if isinstance(data, str):
        # No negative values
        if '-' in data:
            raise ValueError(f"String input {data} to hms_to_string() must be in valid, positive timedelta format.")

        # Validate timedelta formatting, part 1
        if not (re.search('\d+? days, \d+?:\d+?:\d+?', data) or
                re.search('\d day, \d+?:\d+?:\d+?', data) or
                re.search('\d+?:\d+?:\d+?', data)):
            raise ValueError(f"String input {data} to hms_to_string() must be in a valid timedelta format. "
                             f"Ex: '7:19:02' or '1 day, 7:19:02' or '2 days, 7:19:02'")

        # Extract the number of days (if any)
        # Beyond this point, data is a string in the H:MM:SS format
        if 'day' in data.lower():
            full_split = data.split(" ")
            days = int(full_split[0])

            # Remainder of the input can be handled with the hh:mm:ss strings
            data = full_split[2]
        else:
            days = 0

        # Validate timedelta formatting, part 2
        # Converting to datetime ensures 0 >= hours >= 23, 0>= minutes >= 59, and 0>= seconds >= 59
        try:
            format_validation = datetime.strptime(data, "%H:%M:%S")
        except ValueError:
            raise ValueError(f"String input {data} to hms_to_string() must be a valid H:MM:SS timestamp format.")

        try:
            data = data.split(":")
            hours = int(data[0])  # No need for 'or 0' because data was already validated by the .strptime function
            minutes = int(data[1])
            seconds = int(data[2])
        except (TypeError, ValueError) as e:
            raise e(f"Input {data} {type(data[0])} to hms_to_string() must convert to int.")

    # Now that days/hours/minutes/seconds are all defined, build the string!
    if days == 0:
        result = ''
    elif days == 1:
        result = f'{days} day'
    else:
        result = f'{days} days'

    result += ', ' if hours >= 1 and result != '' else ''
    if hours == 0:
        pass
    elif hours == 1:
        result += f'{hours} hr'
    else:
        result += f'{hours} hrs'

    result += ', ' if minutes >= 1 and result != '' else ''
    if minutes == 0:
        logger.debug(f"End of hms_to_string(), returning: {result}")
        return result
    else:
        result += f'{minutes} min'
        logger.debug(f"End of hms_to_string(), returning: {result}")
        return result

    # We don't care about seconds
