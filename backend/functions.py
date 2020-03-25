"""Collection of functions used across the breadsheet project."""
from backend.global_logger import logger
from datetime import datetime, timedelta
from pynamodb.attributes import ListAttribute


def generate_new_id() -> str:
    """Primary key (id) is a 17-digit epoch timestamp.  Ex: 1560043140.168794"""
    # Ensure all ids are the same length.  Timestamps can end in 0, which the system truncates.
    new_id = ""
    while len(new_id) != 17:
        new_id = str(datetime.utcnow().timestamp())
    return new_id


def set_when(steps: ListAttribute(), when: datetime) -> list:
    """
    Calculate when each step should begin, using a list of steps plus the benchmark time.
    Return a list of steps.
    """
    logger.debug(f"Start of set_when(), with when={when}, {len(steps)} steps, all steps: {steps}")
    i = 0
    for step in steps:
        logger.debug(f"Looking at step {step.number}, when={when.strftime('%Y-%m-%d %H:%M:%S')}, "
                     f"then_wait={step.then_wait}")

        # Set the 'when' for this step
        step.when = when.strftime('%Y-%m-%d %H:%M:%S')

        # Create a timedelta object for then_wait to simplify formulas
        step.then_wait = 0 if step.then_wait is None else int(step.then_wait)

        # Increment
        when += timedelta(seconds=step.then_wait)

        step.then_wait_ui = str(timedelta(seconds=step.then_wait))
        i += 1

        logger.debug(f"Finished step {step.number}")

    logger.debug(f"End of set_when(), returning: {steps}")
    return steps


def replace_text(text, rep_list, scope):
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
