"""Common functions used across the breadsheet project."""
from backend.global_logger import logger


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
