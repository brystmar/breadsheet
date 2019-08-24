from app import logger
from datetime import datetime, timedelta


# def sort_list_of_dictionaries(unsorted_list, key_to_sort_by, reverse=False) -> list:
#     return sorted(unsorted_list, key=lambda k: k[key_to_sort_by], reverse=reverse)


def generate_new_id() -> str:
    """Primary key (id) is a 17-digit epoch timestamp.  Ex: 1560043140.168794"""
    # For sanity, ensure all ids are the same length.  Timestamps occasionally end in 0, which the system truncates.
    new_id = ""
    while len(new_id) != 17:
        new_id = f"{datetime.utcnow().timestamp()}"
    return new_id


def seconds_to_hms(seconds_input) -> list:
    """Converts a raw number of seconds (int/str) to a list of strings: [hours, minutes, seconds]."""
    logger.debug(f"Start of seconds_to_hms(), with: {seconds_input}")
    result = timedelta(seconds=int(seconds_input)).__str__().split(":")
    logger.debug(f"End of seconds_to_hms(), returning: {result}")
    return result


def hms_to_seconds(hms) -> int:
    """Convert an int/str list of [hours, minutes, seconds] to a total number of seconds (int)."""
    result = int(timedelta(hours=int(hms[0] or 0), minutes=int(hms[1] or 0), seconds=int(hms[2] or 0)).total_seconds())
    return result


def hms_to_string(data) -> str:
    """Convert an int/str list of [hrs, min, sec] to a human-readable string.  Yet again, because I'm a newbie."""
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
