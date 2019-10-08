from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, IntegerField, SelectField, TextAreaField
from wtforms.fields.html5 import DateField, TimeField
from wtforms.validators import DataRequired, Length, NumberRange, Optional


class RecipeForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()], render_kw={'autofocus': True})
    author = StringField('Author')
    source = StringField('Source')
    difficulty = SelectField('Difficulty', validators=[DataRequired()], render_kw={'class': 'list-group'},
                             default='Intermediate', choices=[('Beginner', 'Beginner'),
                                                              ('Intermediate', 'Intermediate'),
                                                              ('Advanced', 'Advanced')])
    submit = SubmitField('Add Recipe', render_kw={'class': 'btn btn-primary'})

    def __repr__(self):  # tells python what to display for objects of this class while debugging
        return f'<RecipeForm: {self.name}>'


class StepForm(FlaskForm):
    number = IntegerField('Step #', validators=[DataRequired(), NumberRange(min=0)], id="addStep_number")
    text = StringField('Directions', validators=[DataRequired(), Length(max=128)], id="addStep_directions",
                       render_kw={'autofocus': True})
    then_wait_h = IntegerField('Then Wait...', validators=[Optional(), NumberRange(min=0, max=999)],
                               id="addStep_then_wait_h", render_kw={'placeholder': 'h'})
    then_wait_m = IntegerField('Then Wait...', validators=[Optional(), NumberRange(min=0, max=999)],
                               id="addStep_then_wait_m", render_kw={'placeholder': 'm'})
    note = StringField('Notes', id="addNote")
    submit = SubmitField('Add Step', render_kw={'class': 'btn btn-primary'})

    def __repr__(self):
        return f'<StepForm #{self.number} for recipe: {self.name}>, twh={self.then_wait_h}, twm={self.then_wait_m}'


class ThenWaitForm(FlaskForm):
    step_number = IntegerField('Step Number')
    then_wait_h = StringField('Then Wait...', validators=[NumberRange(min=0, max=999)], render_kw={'placeholder': 'h'})
    then_wait_m = StringField('Then Wait...', validators=[NumberRange(min=0, max=999)], render_kw={'placeholder': 'm'})

    def __repr__(self):
        return f'<ThenWaitForm for step {self.step_number}>, twh={self.then_wait_h}, twm={self.then_wait_m}'


class StartFinishForm(FlaskForm):
    recipe_id = IntegerField('Recipe ID')
    start_date = DateField('Start Date', id='start_date', render_kw={'placeholder': 'date', 'disabled': ''})
    start_time = TimeField('Start Time', id='start_time', render_kw={'disabled': ''})
    finish_date = DateField('Finish Date', id='finish_date', render_kw={'placeholder': 'date'})
    finish_time = TimeField('Finish Time', id='finish_time')
    solve_for_start = SelectField('Solve For', id='solve_for_start', default='1', validators=[DataRequired()],
                                  choices=[('1', 'Start Time'), ('0', 'Finish Time')], render_kw={'autofocus': True})

    def __repr__(self):
        return f'<StartFinishForm for recipe_id: {self.recipe_id}>'


# TODO: Find a better way to display Paprika recipe info on each page
paprika_recipe_ids = ['1560122081.000008',
                      '1560122082.002055',
                      '1560122083.005019',
                      '1560122084.005266',
                      '1560122085.006554'
                      ]
