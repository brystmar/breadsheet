from flask_wtf import FlaskForm
from wtforms import SubmitField, TextAreaField


class ConvertTextForm(FlaskForm):
    ingredients_input = TextAreaField('Input', id='ingredients_input', render_kw={'autofocus': True})
    ingredients_output = TextAreaField('Output', id='ingredients_output')
    directions_input = TextAreaField('Input', id='directions_input')
    directions_output = TextAreaField('Output', id='directions_output')
    submit = SubmitField('Convert')

    def __repr__(self):
        return '<ConvertText form>'
