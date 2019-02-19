from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, TextAreaField, IntegerField, DecimalField, SelectField
from wtforms.validators import DataRequired, ValidationError, Length, Optional, NumberRange
from app.models import Recipe


class RecipeForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), Length(min=5, max=64)])
    author = StringField('Author', validators=[Length(max=64)])
    source = StringField('Source', validators=[Length(max=128)])
    difficulty = SelectField('Difficulty', validators=[DataRequired()], default='M', choices=[('E', 'Easy'), ('M', 'Medium'), ('H', 'Hard')])
    submit = SubmitField('Add Recipe')

    # ensure recipe name is unique
    def validate_recipename(self, name):
        recipe_name = Recipe.query.filter_by(name=name.data).first()
        if recipe_name is not None or recipe_name.lower() == name.data.lower():
            raise ValidationError('Recipe name is already in use.  Please enter a unique name.')

    def __repr__(self):  # tells python how to print objects of this class to the console while debugging
        return '<RecipeForm: {}>'.format(self.name)


class StepForm(FlaskForm):
    recipe_id = IntegerField('Recipe ID')
    number = IntegerField('Step Number')
    text = TextAreaField('Directions', validators=[DataRequired(), Length(max=512)])
    then_wait = DecimalField('Then Wait...', validators=[Optional(), NumberRange(min=0)])
    then_wait_units = SelectField('Units', validators=[DataRequired()], default='minutes',
                                  choices=[('hours', 'Hours'), ('minutes', 'Minutes'), ('seconds', 'Seconds')])
    wait_time_range = StringField('Time Range')
    submit = SubmitField('Add Step')

    def __repr__(self):
        return '<StepForm #{} for recipe_id: {}>'.format(self.number, self.name)


class ConvertTextForm(FlaskForm):
    ingredients_input = TextAreaField('Ingredients Input')
    ingredients_output = TextAreaField('Ingredients Output')
    convert_ingredients = SubmitField('Convert Ingredients')

    directions_input = TextAreaField('Directions Input')
    directions_output = TextAreaField('Directions Output')
    convert_directions = SubmitField('Convert Directions')


    def __repr__(self):
        return '<ConvertText form>'
