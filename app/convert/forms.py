from flask_wtf import FlaskForm
from wtforms import SubmitField, TextAreaField


class ConvertTextForm(FlaskForm):
    ingredients_input = TextAreaField('Ingredients Input', id='ingredients_input', render_kw={'autofocus': True})
    ingredients_output = TextAreaField('Ingredients Output', id='ingredients_output')
    directions_input = TextAreaField('Directions Input', id='directions_input')
    directions_output = TextAreaField('Directions Output', id='directions_output')
    submit = SubmitField('Convert', id='convert_button')
    # reset = SubmitField('Reset', id='reset', onclick='clearFields();')

    def __repr__(self):
        return '<ConvertText form>'
