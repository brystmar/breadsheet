from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, TextAreaField, IntegerField, SelectField, SelectMultipleField
from wtforms.fields.html5 import DateTimeField, DateField, TimeField
from wtforms.validators import DataRequired, ValidationError, Length, Optional, NumberRange
from app.models import Recipe


class RecipeForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), Length(min=5, max=64)], render_kw={'autofocus': True})
    author = StringField('Author', validators=[Length(max=64)])
    source = StringField('Source', validators=[Length(max=128)])
    difficulty = SelectField('Difficulty', validators=[DataRequired()], default='M',
                             choices=[('E', 'Easy'), ('M', 'Medium'), ('H', 'Hard')])
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
    text = TextAreaField('Directions', validators=[DataRequired(), Length(max=512)], render_kw={'autofocus': True})
    then_wait_h = IntegerField('Then Wait...', validators=[Optional(), NumberRange(min=0, max=999)], render_kw={'placeholder': 'h'})
    then_wait_m = IntegerField('Then Wait...', validators=[Optional(), NumberRange(min=0, max=999)], render_kw={'placeholder': 'm'})
    then_wait_s = IntegerField('Then Wait...', validators=[Optional(), NumberRange(min=0, max=999)], render_kw={'placeholder': 's'})
    wait_time_range = StringField('Time Range')
    submit = SubmitField('Add Step')

    def __repr__(self):
        return '<StepForm #{} for recipe_id: {}>'.format(self.number, self.name)


class ConvertTextForm(FlaskForm):
    ingredients_input = TextAreaField('Input', id='ingredients_input', render_kw={'autofocus': True})
    ingredients_output = TextAreaField('Output', id='ingredients_output')
    directions_input = TextAreaField('Input', id='directions_input')
    directions_output = TextAreaField('Output', id='directions_output')
    submit = SubmitField('Convert')

    def __repr__(self):
        return '<ConvertText form>'


class ThenWaitForm(FlaskForm):
    step_id = IntegerField('Step Number')
    then_wait_h = IntegerField('Then Wait...', validators=[NumberRange(min=0, max=999)], render_kw={'placeholder': 'h'})
    then_wait_m = IntegerField('Then Wait...', validators=[NumberRange(min=0, max=999)], render_kw={'placeholder': 'm'})
    then_wait_s = IntegerField('Then Wait...', validators=[NumberRange(min=0, max=999)], render_kw={'placeholder': 's'})

    def __repr__(self):
        return '<ThenWait form>'


class StartFinishForm(FlaskForm):
    recipe_id = IntegerField('Recipe ID')
    start_date = DateField('Start Date', id='start_date', render_kw={'placeholder': 'date'})
    start_time = TimeField('Start Time', id='start_time')
    finish_date = DateField('Finish Date', id='finish_date', render_kw={'placeholder': 'date'})
    finish_time = TimeField('Finish Time', id='finish_time')
    solve_for_start = SelectField('Solve For', id='solve_for_start', default='F', validators=[DataRequired()],
                                  choices=[('S', 'Start Time'), ('F', 'Finish Time')])

    def __repr__(self):
        return '<Start & End Times form>'
