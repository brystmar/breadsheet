from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, TextAreaField, IntegerField, DecimalField
from wtforms.validators import DataRequired, ValidationError, Length
from app.models import Recipe


class RecipeForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), Length(min=5, max=64)])
    author = StringField('Author', validators=[Length(max=64)])
    source = StringField('Source', validators=[Length(max=128)])
    difficulty = StringField('Difficulty', validators=[Length(max=1)])
    submit = SubmitField('Add Recipe')

    # ensure recipe name is unique
    def validate_recipename(self, name):
        recipe_name = Recipe.query.filter_by(name=name.data).first()
        if recipe_name is not None or recipe_name.lower() == name.data.lower():
            raise ValidationError('Recipe name is already in use.  Please enter a unique name.')

    def __repr__(self):  # tells python how to print objects of this class to the console while debugging
        return '<RecipeForm: {}>'.format(self.name)


class StepForm(FlaskForm):
    recipe_id = IntegerField('recipe_id', validators=[DataRequired()])
    number = IntegerField('Step Number')
    text = TextAreaField('Directions', validators=[DataRequired(), Length(max=512)])
    then_wait = DecimalField('Then Wait...', places=2)
    wait_time_range = StringField('Time Range')
    submit = SubmitField('Add Step')

    def __repr__(self):  # tells python how to print objects of this class to the console while debugging
        return '<StepForm #{} for recipe_id: {}>'.format(self.number, self.name)
