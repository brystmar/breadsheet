from app.convert import bp
from app.convert.forms import ConvertTextForm
from app.models import Replacement
from flask import render_template, request
# import pyperclip
from global_logger import glogger
import logging

logger = glogger
logger.setLevel(logging.DEBUG)


@bp.route('/convert', methods=['GET', 'POST'])
def convert():
    """Page accept text to convert for both ingredients & directions, does the conversion, and returns the result.

    Once finished, the user may copy the output to the clipboard.
    """

    logger.info("Start of the convert() function, request method: {}".format(request.method))
    form = ConvertTextForm(prefix="form1")

    if form.is_submitted() and form.submit.data:
        logger.info("Convert form submitted.")

        if form.ingredients_input.data != "":
            ingredients = replace_text(form.ingredients_input.data, 'i')
        else:
            logger.debug("Ingredients field was blank.")
            ingredients = form.ingredients_input.data

        if form.directions_input.data != "":
            directions = replace_text(form.directions_input.data, 'd')
        else:
            logger.debug("Directions field was blank.")
            directions = form.directions_input.data

        form.ingredients_output.data = ingredients
        form.directions_output.data = directions

        # copy converted data to the clipboard
        if len(ingredients) > 0 and len(directions) > 0:
            clip = ingredients + '\n\n' + directions
            # pyperclip.copy(clip)
            # flash('Copied to clipboard')
            # logger.info("Copied to clipboard.")
        elif len(ingredients) > 0:
            clip = ingredients
            # pyperclip.copy(clip)
            # flash('Copied to clipboard')
            # logger.info("Copied to clipboard.")
        elif len(directions) > 0:
            clip = directions
            # pyperclip.copy(clip)
            # flash('Copied to clipboard')
            # logger.info("Copied to clipboard.")

    elif request.method == 'GET':
        # logger.debug("Went to the 'elif' GET block")
        pass

    logger.debug("End of the convert() function for form1.")
    return render_template('convert/convert_text.html', title='Convert Text for Paprika Recipes', form=form)


def replace_text(text, scope):
    """Execute replacements in the provided text."""
    logger.debug("Starting replace_text(), with scope: {s}, text: {t}".format(s=scope, t=text))

    replacements_list = Replacement.query.filter_by(scope=scope).all()
    i = 0
    for r in replacements_list:
        new_text = text.replace(r.old, r.new)
        if text != new_text:
            logger.debug("Replaced {o} with {n}".format(o=r.old, n=r.new))
            text = new_text
            i += 1

    logger.debug("End of replace_text() with {i} items replaced.".format(i=i))
    return text
