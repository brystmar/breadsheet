# when connecting from a web browser, show the Hello World page
from flask import render_template, flash, redirect, url_for, request
from sqlalchemy import func
from werkzeug.urls import url_parse
from datetime import datetime, timedelta

from app import breadapp, db
from app.forms import RecipeForm, StepForm
from app.models import Recipe, Step, Difficulty


now = datetime.now()

# map the desired URL to this function
@breadapp.route('/')
@breadapp.route('/index')
@breadapp.route('/breadsheet')
def index():
    recipes = add_recipe_ui_fields(Recipe.query.order_by('id').all())

    return render_template('index.html', title='Breadsheet Home', recipes=recipes)


@breadapp.route('/recipe')
def view_recipe():
    recipe_id = request.args.get('id') or 1
    recipe = add_recipe_ui_fields(Recipe.query.filter_by(id=recipe_id).first())
    steps = set_when(Step.query.filter_by(recipe_id=recipe_id).order_by(Step.number).all(), now)

    return render_template('steps.html', title='View Recipe', recipe=recipe, steps=steps)


@breadapp.route('/add_recipe', methods=['GET', 'POST'])
def add_recipe():
    rform = RecipeForm()

    if rform.validate_on_submit():
        rdata = Recipe(name=rform.name.data, author=rform.author.data, source=rform.source.data, difficulty=rform.difficulty.data,
                       date_added=datetime.utcnow())
        db.session.add(rdata)
        db.session.commit()

        recipe_id = rdata.id
        return redirect(url_for('add_step') + '?id={}'.format(recipe_id))
    return render_template('add_recipe.html', title='Add Recipe', rform=rform)


@breadapp.route('/add_step', methods=['GET', 'POST'])
def add_step():
    sform = StepForm()
    recipe_id = request.args.get('id') or 1
    sform.recipe_id.data = recipe_id

    recipe = add_recipe_ui_fields(Recipe.query.filter_by(id=recipe_id).first())
    steps = set_when(Step.query.filter_by(recipe_id=recipe_id).order_by(Step.number).all(), now)

    if sform.validate_on_submit():
        # convert then_wait decimal value to seconds
        units = sform.then_wait_units.data
        then_wait = sform.then_wait.data
        if then_wait is None:
            then_wait = 0
        elif units == 'minutes':
            then_wait = int(round(then_wait * 60, 0))
        elif units == 'hours':
            then_wait = int(round(then_wait * 60 * 60, 0))

        sdata = Step(recipe_id=recipe_id, number=sform.number.data, text=sform.text.data, then_wait=then_wait,
                     wait_time_range=sform.wait_time_range.data)

        db.session.add(sdata)
        db.session.commit()

        return redirect(url_for('add_step') + '?id={}'.format(recipe_id))

    elif request.method == 'GET':  # pre-populate the form with the recipe info and any existing steps
        # increment from the max step number
        max_step = Step.query.filter_by(recipe_id=recipe_id).order_by(Step.number.desc()).first()
        if max_step is None:
            sform.number.data = 1
        else:
            sform.number.data = max_step.number + 1

    return render_template('add_step.html', title='Add Step', recipe=recipe, steps=steps, sform=sform)


def time_string(num):
    # accepts a number of seconds (int), returns a formatted string with hrs/min/sec
    if num is None: return ''
    else:
        hours = num // 3600
        if hours == 0:
            hstr = ''
        else:
            hstr = str(hours) + 'h'
        num %= 3600

        minutes = num // 60
        if minutes == 0:
            mstr = ''
        else:
            mstr = str(minutes) + 'm'
        num %= 60

        seconds = num
        if seconds == 0:
            sstr = ''
        else:
            sstr = str(seconds) + 's'

        return hstr + mstr + sstr


def set_when(steps, when):
    # calculates when each step should begin
    # also converts raw seconds to a text string, stored in a UI-specific value for 'then_wait'
    i = 0
    for s in steps:
        if i == 0:
            s.when = when.strftime('%Y-%m-%d %H:%M')
            s.then_wait_ui = time_string(s.then_wait)
            when += timedelta(seconds=s.then_wait)
        else:
            if s.then_wait is None or s.then_wait == 0:
                s.when = when.strftime('%Y-%m-%d %H:%M')
                s.then_wait_ui = '--'
            else:
                s.when = when.strftime('%Y-%m-%d %H:%M')
                s.then_wait_ui = time_string(s.then_wait)
                when += timedelta(seconds=s.then_wait)
        i += 1

    return steps


def difficulty_abbrev(abbrev, values):
    # return the difficulty text from an abbreviation
    for v in values:
        if v.id == abbrev:
            return v.text
    return '--'


def add_recipe_ui_fields(data):
    # populates the difficulty_ui, date_added_ui, start_time, & end_time fields
    # total_time = Step.query.filter_by(recipe_id=1).with_entities(func.sum('then_wait'))
    difficulty_values = Difficulty.query.all()
    if isinstance(data, list):
        for d in data:
            d.difficulty_ui = difficulty_abbrev(d.difficulty, difficulty_values)
            d.date_added_ui = d.date_added.strftime('%Y-%m-%d %H:%M')
    else:
        data.difficulty_ui = difficulty_abbrev(data.difficulty, difficulty_values)
        data.date_added_ui = data.date_added.strftime('%Y-%m-%d %H:%M')

        total_time = db.engine.execute("SELECT sum(then_wait) FROM step WHERE recipe_id = {}".format(data.id)).first()[0]
        if total_time is None:
            data.start_time = '--'
            data.end_time = '--'
        else:
            data.start_time = now.strftime('%Y-%m-%d %H:%M')
            data.end_time = (now + timedelta(seconds=total_time)).strftime('%Y-%m-%d %H:%M')

    return data
