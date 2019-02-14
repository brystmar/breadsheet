from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, TextAreaField, IntegerField, DecimalField
from wtforms.validators import DataRequired, ValidationError, Length
from app.models import Recipe


class RecipeForm(FlaskForm):
    name = StringField('Recipe Name', validators=[DataRequired(), Length(min=5, max=64)])
    author = StringField('Author', validators=[Length(min=0, max=64)])
    source = StringField('Source', validators=[Length(min=0, max=128)])
    difficulty = StringField('Difficulty', validators=[Length(min=0, max=6)])
    submit = SubmitField('Add Recipe')

    # ensure recipe name is unique
    def validate_recipename(self, name):
        recipe_name = Recipe.query.filter_by(name=name.data).first()
        if recipe_name is not None:
            raise ValidationError('Recipe name is already in use.  Please enter a unique name.')

    def __repr__(self):  # tells python how to print objects of this class for debugging
        return '<RecipeForm: {}>'.format(self.name)


class StepForm(FlaskForm):
    recipe_id = IntegerField('recipe_id', validators=[DataRequired(), Length(min=1, max=8)])
    number = IntegerField('Step Number', validators=[DataRequired(), Length(min=1, max=3)])
    text = TextAreaField('Directions', validators=[DataRequired(), Length(min=1, max=512)])
    then_wait = DecimalField('Then Wait... (minutes)', places=2)

