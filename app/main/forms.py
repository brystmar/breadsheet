from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, TextAreaField, IntegerField, SelectField
from wtforms.fields.html5 import DateField, TimeField
from wtforms.validators import DataRequired, ValidationError, Length, NumberRange, Optional
from app.models import RecipeRDB


class RecipeForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), Length(min=5, max=64)], render_kw={'autofocus': True})
    author = StringField('Author', validators=[Length(max=64)])
    source = StringField('Source', validators=[Length(max=128)])
    difficulty = SelectField('Difficulty', validators=[DataRequired()], default='Medium',
                             choices=[('Easy', 'Easy'), ('Medium', 'Medium'), ('Hard', 'Hard')])
    submit = SubmitField('Add Recipe', render_kw={'class': 'btn btn-primary'})

    # ensure recipe name is unique
    def validate_recipename(self, name):
        recipe_name = RecipeRDB.query.filter_by(name=name.data).first()
        if recipe_name is not None or recipe_name.lower() == name.data.lower():
            raise ValidationError('Recipe name is already in use.  Please enter a unique name.')

    def __repr__(self):  # tells python how to print objects of this class to the console while debugging
        return '<RecipeForm: {}>'.format(self.name)


class StepForm(FlaskForm):
    recipe_id = IntegerField('Recipe ID')
    number = IntegerField('Step #', id="addStep_number")
    text = TextAreaField('Directions', validators=[DataRequired(), Length(max=512)], id="addStep_directions",
                         render_kw={'autofocus': True})
    then_wait_h = IntegerField('Then Wait...', validators=[Optional(), NumberRange(min=0, max=999)],
                               id="addStep_then_wait_h", render_kw={'placeholder': 'h'})
    then_wait_m = IntegerField('Then Wait...', validators=[Optional(), NumberRange(min=0, max=999)],
                               id="addStep_then_wait_m", render_kw={'placeholder': 'm'})
    wait_time_range = StringField('Time Range', id="addStep_time_range")
    submit = SubmitField('Add Step', render_kw={'class': 'btn btn-primary'})

    def __repr__(self):
        return '<StepForm #{} for recipe_id: {}>'.format(self.number, self.name)


class ThenWaitForm(FlaskForm):
    step_id = IntegerField('Step Number')
    then_wait_h = IntegerField('Then Wait...', validators=[NumberRange(min=0, max=999)], render_kw={'placeholder': 'h'})
    then_wait_m = IntegerField('Then Wait...', validators=[NumberRange(min=0, max=999)], render_kw={'placeholder': 'm'})

    def __repr__(self):
        return '<ThenWait form for step_id: {s}>'.format(s=self.step_id)


class StartFinishForm(FlaskForm):
    recipe_id = IntegerField('Recipe ID')
    start_date = DateField('Start Date', id='start_date', render_kw={'placeholder': 'date'})
    start_time = TimeField('Start Time', id='start_time')
    finish_date = DateField('Finish Date', id='finish_date', render_kw={'placeholder': 'date', 'disabled': ''})
    finish_time = TimeField('Finish Time', id='finish_time', render_kw={'disabled': ''})
    solve_for_start = SelectField('Solve For', id='solve_for_start', default='1', validators=[DataRequired()],
                                  choices=[('1', 'Start Time'), ('0', 'Finish Time')], render_kw={'autofocus': True})

    def __repr__(self):
        return '<Start & End Times form for recipe_id: {}>'.format(self.recipe_id)
