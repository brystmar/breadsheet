import pyperclip
from app.convert import bp
from app.convert.forms import ConvertTextForm
from app.models import Replacement
from flask import render_template, flash, request


@bp.route('/convert', methods=['GET', 'POST'])
def convert():
    form = ConvertTextForm(prefix="form1")

    if form.is_submitted() and form.submit.data:
        ingredients = replace_text(form.ingredients_input.data, 'i')
        directions = replace_text(form.directions_input.data, 'd')

        form.ingredients_output.data = ingredients
        form.directions_output.data = directions

        # copy converted data to the clipboard
        if len(ingredients) > 0 and len(directions) > 0:
            clip = ingredients + '\n\n' + directions
            pyperclip.copy(clip)
            flash('Copied to clipboard')
        elif len(ingredients) > 0:
            clip = ingredients
            pyperclip.copy(clip)
            flash('Copied to clipboard')
        elif len(directions) > 0:
            clip = directions
            pyperclip.copy(clip)
            flash('Copied to clipboard')

    elif request.method == 'GET':
        # print("Went to the GET block form1")
        pass

    return render_template('convert/convert_text.html', title='Convert Text for Paprika Recipes', form=form)


def replace_text(text, scope):
    # execute replacements in the provided text
    replist = Replacement.query.filter_by(scope=scope).all()
    for r in replist:
        text = text.replace(r.old, r.new)
    return text
