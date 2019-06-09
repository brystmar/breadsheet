from app import db, logger
from app.convert import bp
from app.convert.forms import ConvertTextForm
from app.models import ReplacementRDB
from flask import render_template, request
# import pyperclip


@bp.route('/convert', methods=['GET', 'POST'])
def convert():
    """Convert common replacements for both ingredients & directions; optionally copies the results to the clipboard."""

    logger.info(f"Start of the convert() function, request method: {request.method}")
    form = ConvertTextForm(prefix="ConvertTextForm")

    if form.is_submitted() and form.submit.data:
        logger.info("Convert form submitted.")

        # Grab the entire list from the db
        response = db.Table('Replacement').scan()

        # Check the response code
        response_code = response['ResponseMetadata']['HTTPStatusCode']
        logger.debug(f"Scanned the Replacement table, HTTPStatusCode={response_code}")
        if response_code != 200:
            logger.warning(f"DynamoDB error: HTTPStatusCode={response_code}")
            logger.debug(f"Full response log:\n{response['ResponseMetadata']}")

        logger.debug(f"Retrieved {len(response['Items'])} replacements.")
        replacements_list = response['Items']

        if form.ingredients_input.data != "":
            ingredients = replace_text(form.ingredients_input.data, replacements_list, 'ingredients')
        else:
            logger.debug("Ingredients field was blank.")
            ingredients = form.ingredients_input.data

        if form.directions_input.data != "":
            directions = replace_text(form.directions_input.data, replacements_list, 'directions')
        else:
            logger.debug("Directions field was blank.")
            directions = form.directions_input.data

        form.ingredients_output.data = ingredients
        form.directions_output.data = directions

        # TODO: Known issue with pyperclip prevents us from copying to the clipboard via this method.
        #  Currently handling this in JS, would love to find a workaround in Python.
        # copy converted data to the clipboard
        # if len(ingredients) > 0 and len(directions) > 0:
        #     clip = ingredients + '\n\n' + directions
        #     pyperclip.copy(clip)
        #     flash('Copied to clipboard')
        #     logger.info("Copied to clipboard.")
        # elif len(ingredients) > 0:
        #     clip = ingredients
        #     pyperclip.copy(clip)
        #     flash('Copied to clipboard')
        #     logger.info("Copied to clipboard.")
        # elif len(directions) > 0:
        #     clip = directions
        #     pyperclip.copy(clip)
        #     flash('Copied to clipboard')
        #     logger.info("Copied to clipboard.")

    elif request.method == 'GET':
        # logger.debug("Went to the 'elif' GET block")
        pass

    logger.debug("End of the convert() function for form1.")
    return render_template('convert/convert_text.html', title='Convert Text for Paprika Recipes', form=form)


def replace_text(text, rep_list, scope):
    """Execute replacements in the provided text."""
    logger.debug(f"Starting replace_text(), with scope: {scope}, text: {text}")

    count = 0
    for r in rep_list:
        new_text = text.replace(r['old'], r['new'])
        if text != new_text:
            logger.debug(f"Replaced -->{r['old']}<-- with ==>{r['new']}<==")
            text = new_text
            count += 1

    logger.debug(f"End of replace_text(); {count} replacements made")
    return text
