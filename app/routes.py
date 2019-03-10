# when connecting from a web browser, show the Hello World page
from flask import render_template, flash, redirect, url_for, request
from sqlalchemy import func
from werkzeug.urls import url_parse
from datetime import datetime, timedelta
import json
import pyperclip
from wtforms.fields.html5 import DateField

from app import breadapp, db
from app.forms import RecipeForm, StepForm, ConvertTextForm, ThenWaitForm, StartFinishForm
from app.models import Recipe, Step, Difficulty, Replacement
now = datetime.now()


# map the desired URL to this function
@breadapp.route('/')
@breadapp.route('/index')
@breadapp.route('/breadsheet')
def index():
    recipes = add_recipe_ui_fields(Recipe.query.order_by('id').all())
    return render_template('index.html', title='Breadsheet Home', recipes=recipes)


@breadapp.route('/add_recipe', methods=['GET', 'POST'])
def add_recipe():
    rform = RecipeForm()

    if rform.validate_on_submit():
        rdata = Recipe(name=rform.name.data, author=rform.author.data, source=rform.source.data,
                       difficulty=rform.difficulty.data, date_added=datetime.utcnow())
        db.session.add(rdata)
        db.session.commit()

        recipe_id = rdata.id
        return redirect(url_for('add_step') + '?id={}'.format(recipe_id))
    return render_template('add_recipe.html', title='Add Recipe', rform=rform)


@breadapp.route('/recipe', methods=['GET', 'POST'])
def add_step():
    sform = StepForm()
    recipe_id = request.args.get('id') or 1
    sform.recipe_id.data = recipe_id

    recipe = add_recipe_ui_fields(Recipe.query.filter_by(id=recipe_id).first())
    steps = set_when(Step.query.filter_by(recipe_id=recipe_id).order_by(Step.number).all(), recipe.start_time)
    twforms = create_tw_forms(steps)
    seform = create_start_finish_forms(recipe)
    # steps_js = json.dumps(create_steps_js(steps))

    if sform.validate_on_submit():
        # convert then_wait decimal value to seconds
        then_wait = hms_to_seconds([sform.then_wait_h.data, sform.then_wait_m.data, sform.then_wait_s.data])

        sdata = Step(recipe_id=recipe_id, number=sform.number.data, text=sform.text.data,
                     then_wait=then_wait, wait_time_range=sform.wait_time_range.data)

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

    return render_template('recipe.html', title=recipe.name, recipe=recipe, steps=steps, sform=sform,
                           seform=seform, twforms=twforms)


@breadapp.route('/convert_text', methods=['GET', 'POST'])
def convert_text():
    print("Top of convert_text")
    form = ConvertTextForm(prefix="form1")

    if form.is_submitted() and form.submit.data:
        ing = replace_text(form.ingredients_input.data, 'i')
        dir = replace_text(form.directions_input.data, 'd')

        form.ingredients_output.data = ing
        form.directions_output.data = dir

        # copy converted data to the clipboard
        if len(ing) > 0 and len(dir) > 0:
            clip = ing + '\n\n' + dir
            pyperclip.copy(clip)
            flash('Copied to clipboard')
        elif len(ing) > 0:
            clip = ing
            pyperclip.copy(clip)
            flash('Copied to clipboard')
        elif len(dir) > 0:
            clip = dir
            pyperclip.copy(clip)
            flash('Copied to clipboard')

    elif request.method == 'GET':
        print("Went to the GET block form1")

    return render_template('convert_text.html', title='Convert Text for Paprika Recipes', form=form)


def replace_text(text, scope):
    # execute replacements in the provided text
    replist = Replacement.query.filter_by(scope=scope).all()
    for r in replist:
        text = text.replace(r.old, r.new)
    return text


def seconds_to_hms(num):
    # accepts a number of seconds (int), returns a three-str list: [hours, minutes, seconds]
    if num is None:
        return ''
    else:
        h = str(num // 3600)
        num %= 3600
        m = str(num // 60)
        num %= 60
        s = str(num)

        result = [h, m, s]
        i = 0
        while i <= 2:
            if result[i] == '0':
                result[i] = '00'
            if len(result[i]) == 1:
                result[i] = '0' + result[i]
            i += 1
    return result


def hms_to_seconds(hms):
    # accepts a three-int list, returns a number of seconds (int)
    if not (isinstance(hms, list) and len(hms) == 3):
        flash('Error in hms_to_seconds function: Invalid input {}.'.format(hms))
        return 0

    try:
        hms[0] = int(hms[0])
        hms[1] = int(hms[1])
        hms[2] = int(hms[2])
        return (hms[0] * 24) + (hms[1] * 60) + (hms[2] * 60)
    except:
        flash('Error in hms_to_seconds function: List values {} cannot be converted to int.'.format(hms))
        return 0


def hms_to_string(data):
    # converts a list of [hrs, min, sec] to a human-readable string
    result = ''
    if data[0] == '00':
        pass
    else:
        result = '{} hrs'.format(data[0])

    if data[1] == '00' and result != '':
        return result  # round off the seconds if it's an even number of hours
    elif data[1] == '00' and result == '':
        pass
    elif result == '':
        result += '{} min'.format(data[1])
    else:
        result += ', {} min'.format(data[1])

    if data[2] == '00' and result != '':
        return result  # round off the seconds if it's an even number of minutes
    elif data[2] == '00' and result == '':
        return result
    elif result == '':
        return '{} sec'.format(data[2])
    else:
        result += ', {} sec'.format(data[2])

    return result


def set_when(steps, when):
    # accepts a list of Step objects, plus the benchmark time, and calculates when each step should begin
    # also converts raw seconds to a text string, stored in a UI-specific value for 'then_wait'
    # returns a list of Steps plus a list of forms
    i = 0
    for s in steps:
        if i == 0:
            s.when = when.strftime('%Y-%m-%d %H:%M')
            s.then_wait_ui = seconds_to_hms(s.then_wait)
            when += timedelta(seconds=s.then_wait)
        else:
            if s.then_wait is None or s.then_wait == 0:
                s.when = when.strftime('%Y-%m-%d %H:%M')
                s.then_wait_ui = seconds_to_hms(s.then_wait)
            else:
                s.when = when.strftime('%Y-%m-%d %H:%M')
                s.then_wait_ui = seconds_to_hms(s.then_wait)
                when += timedelta(seconds=s.then_wait)
        i += 1

    return steps


def difficulty_abbrev(abbrev, values):
    # return the difficulty text from an abbreviation
    for v in values:
        if v.id == abbrev:
            return v.text
    return '--'


def add_recipe_ui_fields(recipe):
    # populates the difficulty_ui, date_added_ui, start_time, & finish_time fields
    # total_time = Step.query.filter_by(recipe_id=1).with_entities(func.sum('then_wait'))

    difficulty_values = Difficulty.query.all()
    if isinstance(recipe, list):  # separate handling for lists
        for r in recipe:
            r = add_recipe_ui_fields(r)
    else:
        recipe.difficulty_ui = difficulty_abbrev(recipe.difficulty, difficulty_values)
        recipe.date_added_ui = recipe.date_added.strftime('%Y-%m-%d %H:%M')
        if recipe.start_time is None:
            recipe.start_time = now
        recipe.start_time = datetime.strptime(recipe.start_time, '%Y-%m-%d %H:%M:%S.%f')
        print(recipe.start_time, type(recipe.start_time))
        recipe.start_time_ui = dt_ui(recipe.start_time)

        sql = "SELECT sum(then_wait) FROM step WHERE recipe_id = {}".format(recipe.id)
        recipe.total_time = db.engine.execute(sql).first()[0]
        if recipe.total_time is None:
            recipe.finish_time = recipe.start_time
            recipe.finish_time_ui = recipe.start_time_ui
        else:
            recipe.finish_time = recipe.start_time + timedelta(seconds=recipe.total_time)
            recipe.finish_time_ui = dt_ui(recipe.finish_time)
            recipe.total_time_ui = hms_to_string(seconds_to_hms(recipe.total_time))

    return recipe


def dt_ui(dt):
    st = str(dt)
    return st[:st.find('.')-3]


def create_tw_forms(steps):
    twforms = []
    for s in steps:
        tw = ThenWaitForm()
        tw.step_id = s.id
        tw.then_wait_h.data = s.then_wait_ui[0]
        tw.then_wait_m.data = s.then_wait_ui[1]
        tw.then_wait_s.data = s.then_wait_ui[2]
        tw.then_wait = s.then_wait
        twforms.append(tw)
    return twforms


def create_start_finish_forms(recipe):
    seform = StartFinishForm()
    seform.recipe_id.data = recipe.id
    seform.start_date.data = recipe.start_time
    seform.start_time.data = recipe.start_time
    seform.finish_date.data = recipe.finish_time
    seform.finish_time.data = recipe.finish_time
    seform.solve_for_start.data = str(recipe.solve_for_start)

    return seform


def create_steps_js(steps):
    lib = {}
    for s in steps:
        lib[s.id] = s.then_wait
    print(lib)
    return lib
