from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, TextAreaField, IntegerField, SelectField
from wtforms.fields.html5 import DateField, TimeField
from wtforms.validators import DataRequired, ValidationError, Length, NumberRange, Optional


class RecipeForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), Length(min=5, max=64)], render_kw={'autofocus': True})
    author = StringField('Author', validators=[Length(max=64)])
    source = StringField('Source', validators=[Length(max=128)])
    difficulty = SelectField('Difficulty', validators=[DataRequired()], default='Intermediate',
                             choices=[
                                 ('Beginner', 'Beginner'),
                                 ('Intermediate', 'Intermediate'),
                                 ('Advanced', 'Advanced')])
    submit = SubmitField('Add Recipe', render_kw={'class': 'btn btn-primary'})

    # ensure recipe name is unique
    # def validate_recipename(self, name):
    #     recipe_name = RecipeRDB.query.filter_by(name=name.data).first()
    #     if recipe_name is not None or recipe_name.lower() == name.data.lower():
    #         raise ValidationError('Recipe name is already in use.  Please enter a unique name.')

    def __repr__(self):  # tells python how to print objects of this class to the console while debugging
        return f'<RecipeForm: {self.name}>'


class StepForm(FlaskForm):
    number = IntegerField('Step #', id="addStep_number")
    text = TextAreaField('Directions', validators=[DataRequired(), Length(max=512)], id="addStep_directions",
                         render_kw={'autofocus': True})
    then_wait_h = StringField('Then Wait...', validators=[Optional(), NumberRange(min=0, max=999)],
                               id="addStep_then_wait_h", render_kw={'placeholder': 'h'})
    then_wait_m = StringField('Then Wait...', validators=[Optional(), NumberRange(min=0, max=999)],
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


paprika_recipe_ids = ['1560122081.000008_76057b38-a5d4-46dd-948c-5119c1a235f3',
                      '1560122082.002055_c4c907a1-9ff7-4b91-927b-b6e16d5c1bdf',
                      '1560122083.005019_af4f7bd5-ed86-44a2-9767-11f761160dee',
                      '1560122084.005266_2d6bdbc1-b1bb-492f-bca5-90b94eac8bfe',
                      '1560122085.006554_0f74e954-f2e3-475c-aa36-1847cfd3ae9c'
                      ]
