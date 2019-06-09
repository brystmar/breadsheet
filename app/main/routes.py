"""Determine which page(s) to render for each browser request."""
from app import db, sql_db, logger
from app.main import bp
from app.main.forms import RecipeForm, StepForm, ThenWaitForm, StartFinishForm
from app.models import RecipeRDB, StepRDB
from datetime import datetime, date, timedelta
from flask import render_template, redirect, url_for, request, send_from_directory  # , flash
from os import path
from sqlalchemy.sql import text
import boto3
import pytz
PST = pytz.timezone('US/Pacific')


# Map the specified URL to this function
@bp.route('/breadsheet')
@bp.route('/index')
@bp.route('/')
def index():
    logger.info("Start of index()")
    # recipes = add_recipe_ui_fields(RecipeRDB.query.order_by('id').all())

    response = db.Table('Recipe').scan()
    recipes = sort_list_of_dictionaries(response['Items'], 'id')
    logger.debug(f"Sorted recipes returned from dynamodb: {recipes}")

    recipes = add_recipe_ui_fields(recipes)

    logger.info("Rendering the homepage.  End of index()")
    return render_template('index.html', title='Breadsheet: A Recipe Scheduling Tool', recipes=recipes)


@bp.route('/add_recipe', methods=['GET', 'POST'])
def add_recipe():
    logger.info("Start of add_recipe()")

    import uuid
    form = RecipeForm()

    if form.validate_on_submit():
        logger.info("RecipeForm submitted.")

        # Create a JSON document for this new recipe based on the form data submitted
        # Primary key (id) is an underscore-delimited epoch timestamp plus a random UUID
        #   Ex: 1560043140.471138_65f078f6-aea2-41e0-be37-a62e2d5d5474
        new_recipe = {
            'id':           f"{datetime.utcnow().timestamp()}_{uuid.uuid4()}",
            'name':         form.name.data,
            'author':       form.author.data,
            'source':       form.source.data,
            'difficulty':   form.difficulty.data,
            'date_added':   date.today()
            }

        logger.info(f"New recipe data: {new_recipe}")

        db.Table("Recipe").put_item(Item=new_recipe)
        logger.info("Recipe successfully added to the db.")

        logger.debug("Redirecting to the main recipe page.  End of add_recipe().")
        return redirect(url_for("main.recipe") + f"?id={new_recipe['id']}")

    logger.debug("End of add_recipe()")
    return render_template('add_recipe.html', title='Add Recipe', rform=form)


@bp.route('/Images')
@bp.route('/Resources')
@bp.route('/recipe', methods=['GET', 'POST'])
def recipe():
    logger.info(f"Start of recipe(), request method: {request.method}")

    form = StepForm()
    recipe_id = request.args.get('id') or 1
    form.recipe_id.data = recipe_id
    logger.debug(f"Recipe_id: {recipe_id}")

    if recipe_id == 1 and request.args.get('id') != 1:
        logger.info("Error reading the querystring on the /recipe page.")
        logger.debug(f"Read: {request.args.get('id')}")
        logger.debug("Replaced it with 1.")

    recipe = add_recipe_ui_fields(RecipeRDB.query.filter_by(id=recipe_id).first())

    steps = set_when(StepRDB.query.filter_by(recipe_id=recipe_id).order_by(StepRDB.number).all(), recipe.start_time)
    twforms = create_tw_forms(steps)
    seform = create_start_finish_forms(recipe)

    if form.validate_on_submit():
        logger.info("StepForm submitted.")

        # convert then_wait decimal value to seconds
        then_wait = hms_to_seconds([form.then_wait_h.data, form.then_wait_m.data])

        next_step_number = sql_db.engine.execute(text("SELECT max(number) FROM step")).first()[0] + 1
        sdata = StepRDB(id=next_step_number, recipe_id=recipe_id, number=form.number.data, text=form.text.data,
                        then_wait=then_wait, note=form.note.data)
        logger.info(f"New step data: {sdata.__dict__}")

        sql_db.session.add(sdata)
        sql_db.session.commit()
        logger.debug(f"Step {next_step_number} successfully added & committed to the db.")

        logger.debug("Redirecting to the main recipe page.  End of recipe().")
        return redirect(url_for('main.recipe') + f'?id={recipe_id}')

    elif request.method == 'GET':  # pre-populate the form with the recipe info and any existing steps
        logger.debug("Entering the 'elif' section to pre-populate the form w/recipe info and any existing steps.")

        # increment from the max step number
        max_step = StepRDB.query.filter_by(recipe_id=recipe_id).order_by(StepRDB.number.desc()).first()
        if max_step is None:
            form.number.data = 1
        else:
            form.number.data = max_step.number + 1

    logger.debug("Rendering the recipe page.  End of recipe().")
    return render_template('recipe.html', title=recipe.name, recipe=recipe, steps=steps, sform=form,
                           seform=seform, twforms=twforms)


@bp.route('/favicon.ico')
def favicon():
    logger.info("The favicon was requested!! :D")
    return send_from_directory(path.join(bp.root_path, 'static'), 'favicon.ico',
                               mimetype='image/vnd.microsoft.icon')


def sort_list_of_dictionaries(unsorted_list, key_to_sort_by) -> list:
    return sorted(unsorted_list, key=lambda k: k[key_to_sort_by], reverse=False)


def hms_to_seconds(hms) -> int:
    """Convert a list of [hours, minutes, seconds] to a total number of seconds."""
    logger.debug(f"Start of hms_to_seconds(), with: {hms}")
    if not (isinstance(hms, list) and len(hms) == 3):
        logger.warning(f"Error in hms_to_seconds function: Invalid input {hms}.")
        logger.debug("End of hms_to_seconds(), returning 0")
        return 0

    if hms[0] is None:
        hms[0] = 0
    if hms[1] is None:
        hms[1] = 0
    if hms[2] is None:
        hms[2] = 0

    try:
        hms[0] = int(hms[0])
        hms[1] = int(hms[1])
        hms[2] = int(hms[2])
        result = (hms[0] * 60 * 60) + (hms[1] * 60) + (hms[2])

        logger.debug(f"End of hms_to_seconds(), returning: {result}")
        return result
    except TypeError:
        logger.warning(f"Error in hms_to_seconds function: List values {hms} cannot be converted to int.")
        logger.debug("End of hms_to_seconds(), returning 0")
        return 0


def hms_to_string(data) -> str:
    """Convert a list of [hrs, min, sec] to a human-readable string.  Yet again, because I'm a newbie."""
    logger.debug(f"Start of hms_to_string(), with: {data}")
    result = ''
    if data[0] == '00':
        pass
    else:
        result = f'{data[0]} hrs'

    if data[1] == '00' and result != '':
        logger.debug(f"End of hms_to_string(), returning: {result}")
        return result  # round off the seconds if it's an even number of hours
    elif data[1] == '00' and result == '':
        pass
    elif result == '':
        result += f'{data[1]} min'
    else:
        result += f', {data[1]} min'

    if data[2] == '00' and result != '':
        logger.debug(f"End of hms_to_string(), returning: {result}")
        return result  # round off the seconds if it's an even number of minutes
    elif data[2] == '00' and result == '':
        logger.debug(f"End of hms_to_string(), returning: {result}")
        return result
    elif result == '':
        result = f'{data[2]} sec'
        logger.debug(f"End of hms_to_string(), returning: {result}")
        return result
    else:
        result += f', {data[2]} sec'

    logger.debug(f"End of hms_to_string(), returning: {result}")
    return result


def set_when(steps, when) -> list:
    """Accepts a list of Step objects, plus the benchmark time, and calculates when each step should begin.

    Also converts raw seconds to a text string, stored in a UI-specific value for 'then_wait'.
    Returns a list of Steps plus a list of forms.
    """
    logger.debug(f"Start of set_when(), with steps: {steps}, when: {when}")
    i = 0
    for s in steps:
        logger.debug(f"Looking at step: {s.__dict__}")
        if i == 0:
            s.when = when.strftime('%a %H:%M')
            s.then_wait_ui = str(timedelta(seconds=s.then_wait))
            when += timedelta(seconds=s.then_wait)
        else:
            if s.then_wait is None or s.then_wait == 0:
                s.when = when.strftime('%a %H:%M')
                s.then_wait_ui = str(timedelta(seconds=s.then_wait))
            else:
                s.when = when.strftime('%a %H:%M')
                s.then_wait_ui = str(timedelta(seconds=s.then_wait))
                when += timedelta(seconds=s.then_wait)
        i += 1

    logger.debug(f"End of set_when(), returning: {steps}")
    return steps


def add_recipe_ui_fields(recipe):
    """Input: an individual Recipe class, or a list of Recipes.

    Populates the difficulty_ui, date_added_ui, start_time, & finish_time fields."""
    logger.debug(f"Start of add_recipe_ui_fields() for {len(recipe)} recipe(s): {recipe}")

    if isinstance(recipe, list):  # separate handling for lists
        logger.debug(f"Parsing a list of {len(recipe)} recipes.")
        for r in recipe:
            logger.debug(f"Adding UI fields for recipe {r['id']}: {r['name']}")
            r = add_recipe_ui_fields(r)
    else:
        recipe['difficulty_ui'] = recipe['difficulty']
        recipe['date_added_ui'] = str(recipe['date_added'])[:10]
        recipe['start_time'] = PST.localize(datetime.now())
        recipe['start_time_ui'] = recipe['start_time'].strftime('%Y-%m-%d %H:%M:%S')

        recipe['total_time'] = recipe['length']
        logger.debug(f"recipe['total_time'] = {recipe['total_time']}")
        if recipe['total_time'] is None:
            recipe['finish_time'] = recipe['start_time']
            recipe['finish_time_ui'] = recipe['start_time_ui']
            recipe['total_time'] = 0
        else:
            recipe['finish_time'] = recipe['start_time'] + timedelta(seconds=int(recipe['total_time']))
            recipe['finish_time_ui'] = recipe['finish_time'].strftime('%Y-%m-%d %H:%M:%S')
            recipe['total_time_ui'] = hms_to_string(str(timedelta(seconds=int(recipe['total_time']))))
            logger.debug(f"recipe['total_time_ui'] = {recipe['total_time_ui']}")

    logger.debug(f"End of add_recipe_ui_fields(), returning: {recipe}")
    return recipe


def create_tw_forms(steps) -> list:
    """Create a form for the 'then wait...' display for recipe steps, then populate it with data."""
    logger.debug(f"Start of create_tw_forms(), with: {steps}")

    twforms = []
    for s in steps:
        logger.debug(f"Looking at step: {s['number']}")
        tw = ThenWaitForm()
        tw.step_id = s['number']
        tw.then_wait_h.data = s['then_wait_ui']
        tw.then_wait_m.data = s['then_wait_ui']

        # TODO: Fix these fields!  Formerly:
        # tw.then_wait_h.data = s.then_wait_ui[0]
        # tw.then_wait_m.data = s.then_wait_ui[1]

        tw.then_wait = s['then_wait']
        twforms.append(tw)
    logger.debug(f"End of create_tw_forms(), returning {twforms}")
    return twforms


def create_start_finish_forms(recipe) -> StartFinishForm:
    """Set values for the form displaying start & finish times for this recipe."""
    logger.debug(f"Start of create_start_finish_forms(), for: {recipe.__dict__}")

    seform = StartFinishForm()
    seform.recipe_id.data = recipe.id
    seform.start_date.data = recipe.start_time
    seform.start_time.data = recipe.start_time
    seform.finish_date.data = recipe.finish_time
    seform.finish_time.data = recipe.finish_time
    seform.solve_for_start.data = "1"

    logger.debug(f"End of create_start_finish_forms(), returning seform: {seform}")
    return seform
