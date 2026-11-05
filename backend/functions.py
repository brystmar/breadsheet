"""Common functions used across the breadsheet project."""
import logging

logger = logging.getLogger(__name__)


def replace_text(text, rep_list, scope) -> str:
    """Execute replacements in the provided text."""
    count = 0
    for r in rep_list:
        if r.scope == scope:
            new_text = text.replace(r.old, r.new)
            if text != new_text:
                text = new_text
                count += 1

    # The text is the user's own recipe, so only the count is logged
    logger.debug("replace_text(%s): %d replacements made", scope, count)
    return text
