"""Common functions used across the breadsheet project."""
from backend.global_logger import logger
from datetime import datetime
import shortuuid


def generate_new_id(short=False) -> str:
    """
    Recipe primary key (id) is a 17-digit epoch timestamp.  Ex: 1560043140.168794.  Will eventually change to short uuid.
    Step primary key (step_id) is a 22-digit short uuid.
    """
    # Ensure all ids are the same length.  Timestamps can end in 0, which the system truncates.
    new_id = ""
    if short:
        return shortuuid.uuid()
    else:
        while len(new_id) != 17:
            new_id = str(datetime.utcnow().timestamp())
        return new_id


def replace_text(text, rep_list, scope) -> str:
    """Execute replacements in the provided text."""
    logger.info(f"Starting replace_text(), with scope: {scope}, text: {text}")

    count = 0
    for r in rep_list:
        logger.info(f"r.scope: {r.scope}, entered scope: {scope}")
        if r.scope == scope:
            new_text = text.replace(r.old, r.new)
            if text != new_text:
                logger.info(f"Replaced -->{r.old}<-- with ==>{r.new}<==")
                text = new_text
                count += 1

    logger.info(f"End of replace_text() for {scope}; {count} replacements made")
    return text
