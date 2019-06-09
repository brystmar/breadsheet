"""Determine which page(s) to render for each browser request."""
from app import db, sql_db, logger
from app.main import bp
from app.main.forms import RecipeForm, StepForm, ThenWaitForm, StartFinishForm, paprika_recipe_ids
from app.models import RecipeRDB, StepRDB
from boto3.dynamodb.conditions import Key
from config import PST
from datetime import datetime, date, timedelta
from flask import render_template, redirect, url_for, request, send_from_directory  # , flash
from os import path
from sqlalchemy.sql import text


# Map the specified URL to this function
@bp.route('/breadsheet')
@bp.route('/index')
@bp.route('/')
def index():
    logger.info("Start of index()")

    response = db.Table('Recipe').scan()
    recipes = sort_list_of_dictionaries(response['Items'], 'id')
    logger.debug(f"Sorted recipes returned from dynamodb: {recipes}")

    recipes = convert_recipe_strings_to_datetime(recipes)
    recipes = add_recipe_ui_fields(recipes)

    logger.info("Rendering the homepage.  End of index()")
    return render_template('index.html', title='Breadsheet: A Recipe Scheduling Tool', recipes=recipes)


@bp.route('/add_recipe', methods=['GET', 'POST'])
def add_recipe():
    logger.info("Start of add_recipe()")

    form = RecipeForm()

    if form.validate_on_submit():
        logger.info("RecipeForm submitted.")

        # Create a JSON document for this new recipe based on the form data submitted
        new_recipe = {
            'id':           generate_new_id(),
            'name':         form.name.data,
            'author':       form.author.data,
            'source':       form.source.data,
            'difficulty':   form.difficulty.data,
            'date_added':   PST.localize(datetime.now()).strftime("%Y-%m-%d"),
            'start_time':   PST.localize(datetime.now()),
            'steps':        [],
            'length':       0
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

    # Read the recipe_id from the URL querystring
    recipe_id = request.args.get('id') or 1
    form.recipe_id.data = recipe_id
    logger.debug(f"Recipe_id: {recipe_id}")

    if recipe_id == 1 and request.args.get('id') != 1:
        logger.info("Error reading the querystring on the /recipe page.")
        logger.debug(f"Read: {request.args.get('id')}")
        recipe_id = '1560122083.005019_af4f7bd5-ed86-44a2-9767-11f761160dee'  # Detroit pizza
        form.recipe_id.data = recipe_id
        logger.debug(f"Replaced it with the Detroit pizza recipe {recipe_id}.")

    # Retrieve the recipe using the URL querystring's id
    response = db.Table('Recipe').query(KeyConditionExpression=Key('id').eq(recipe_id))
    logger.debug(f"Recipe returned from dynamodb: {response['Items'][0]}")

    recipe = convert_recipe_strings_to_datetime(response['Items'][0])
    recipe = calculate_recipe_length(recipe)
    recipe = add_recipe_ui_fields(recipe)

    # PyCharm went nuts when I replaced recipe_id in the return statement f-string with recipe['id']
    recipe_id = recipe['id']

    steps = set_when(recipe['steps'], recipe['start_time'])
    twforms = create_tw_forms(steps)
    seform = create_start_finish_forms(recipe)

    if form.validate_on_submit():
        logger.info("StepForm submitted.")

        # convert the 'then_wait' decimal value to seconds
        then_wait = hms_to_seconds([form.then_wait_h.data, form.then_wait_m.data])

        new_step = {
            'number': len(steps) + 1,
            'text': form.text.data,
            'then_wait': then_wait,
            'note': form.note.data
        }
        logger.info(f"New step data: {new_step}")

        # Add this new step to the existing list of steps
        recipe['steps'].append(new_step)

        # Update the database
        db.Table("Recipe").put_item(Item=recipe)
        logger.info(f"Recipe {recipe['id']} updated in the db to include step {new_step['number']}.")

        logger.debug("Redirecting to the main recipe page.  End of recipe().")
        return redirect(url_for('main.recipe') + f'?id={recipe_id}')

    elif request.method == 'GET':  # pre-populate the form with the recipe info and any existing steps
        logger.debug("Entering the 'elif' section to pre-populate the form w/recipe info and any existing steps.")

        form.number.data = len(steps) + 1

    logger.debug("Rendering the recipe page.  End of recipe().")
    return render_template('recipe.html', title=recipe['name'], recipe=recipe, steps=steps, sform=form,
                           seform=seform, twforms=twforms, paprika_recipe_ids=paprika_recipe_ids)


@bp.route('/favicon.ico')
def favicon():
    logger.info("The favicon was requested!! :D")
    return send_from_directory(path.join(bp.root_path, 'static'), 'favicon.ico', mimetype='image/vnd.microsoft.icon')


def generate_new_id() -> str:
    """Primary key (id) is a 54-digit, underscore-delimited epoch timestamp plus a random UUID.

    Ex: 1560043140.471138_65f078f6-aea2-41e0-be37-a62e2d5d5474"""
    import uuid
    new_id = ""

    # For my sanity, ensure all ids are the same length.  Timestamps occasionally end in 0, which the system truncates.
    while len(new_id) != 54:
        new_id = f"{datetime.utcnow().timestamp()}_{uuid.uuid4()}"

    return new_id


def sort_list_of_dictionaries(unsorted_list, key_to_sort_by) -> list:
    return sorted(unsorted_list, key=lambda k: k[key_to_sort_by], reverse=False)


def convert_recipe_strings_to_datetime(recipe):
    logger.debug(f"Start of convert_recipe_strings_to_datetime() for: {recipe}")

    # Makes this function recursive if the input was a list
    if isinstance(recipe, list):
        logger.debug(f"Parsing a list of {len(recipe)} recipes.")
        for r in recipe:
            logger.debug(f"Converting fields for recipe {r['id']}: {r['name']}")
            r = convert_recipe_strings_to_datetime(r)
    else:
        recipe['date_added'] = datetime.strptime(recipe['date_added'], '%Y-%m-%d')
        recipe['start_time'] = datetime.strptime(recipe['start_time'], '%Y-%m-%d %H:%M:%S')

    logger.debug(f"End of convert_recipe_strings_to_datetime(), returning: {recipe}")
    return recipe


def calculate_recipe_length(recipe):
    """Add/update the recipe's length (in seconds) by summing the length of each step."""
    logger.debug(f"Start of calculate_recipe_length() for recipe {recipe['id']}")
    try:
        original_length = recipe['length']
    except KeyError:
        original_length = -1

    length = 0
    for step in recipe['steps']:
        length += step['then_wait']

    logger.debug(f"Calculated length: {length}, original length: {original_length}")
    recipe['length'] = length

    # Update the db if the length changed
    if length != original_length:
        db.Table("Recipe").put_item(Item=recipe)
        logger.info(f"Updated recipe {recipe['id']} in the database to reflect its new length.")

    logger.debug("End of calculate_recipe_length()")
    return recipe


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
    """Accepts a list of steps, plus the benchmark time, and calculates when each step should begin.

    Also converts raw seconds to a text string, stored in a UI-specific value for 'then_wait'.
    Returns a list of steps.
    """
    logger.debug(f"Start of set_when(), with steps: {steps}, when: {when}")
    i = 0
    for s in steps:
        logger.debug(f"Looking at step: {s['number']}")
        if i == 0:
            # Define when the first step needs to start
            s['when'] = when.strftime('%a %H:%M')
            s['then_wait_ui'] = str(timedelta(seconds=s['then_wait']))

            # Increment for the next step
            when += timedelta(seconds=s['then_wait'])
        else:
            # Only increment if there's a value for then_wait
            if s['then_wait'] is not None or s['then_wait'] != 0:
                s['when'] = when.strftime('%a %H:%M')
                s['then_wait_ui'] = str(timedelta(seconds=s['then_wait']))
            else:
                s['when'] = when.strftime('%a %H:%M')
                s['then_wait_ui'] = str(timedelta(seconds=s['then_wait']))
                when += timedelta(seconds=s['then_wait'])
        i += 1

    logger.debug(f"End of set_when(), returning: {steps}")
    return steps


def add_recipe_ui_fields(recipe):
    """Input: an individual Recipe class, or a list of Recipes.

    Populates the date_added_ui, start_time, & finish_time fields."""
    logger.debug(f"Start of add_recipe_ui_fields() for {len(recipe)} recipe(s): {recipe}")

    # Makes this function recursive if the input was a list
    if isinstance(recipe, list):
        logger.debug(f"Parsing a list of {len(recipe)} recipes.")
        for r in recipe:
            logger.debug(f"Adding UI fields for recipe {r['id']}: {r['name']}")
            r = add_recipe_ui_fields(r)
    else:
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
        tw.then_wait_h.data = s['then_wait_ui'].split(':')[0]
        tw.then_wait_m.data = s['then_wait_ui'].split(':')[1]

        tw.then_wait = s['then_wait']
        twforms.append(tw)
    logger.debug(f"End of create_tw_forms(), returning {twforms}")
    return twforms


def create_start_finish_forms(recipe) -> StartFinishForm:
    """Set values for the form displaying start & finish times for this recipe."""
    logger.debug(f"Start of create_start_finish_forms(), for {recipe['id']}")

    seform = StartFinishForm()
    seform.recipe_id.data = recipe['id']
    seform.start_date.data = recipe['start_time']
    seform.start_time.data = recipe['start_time']
    seform.finish_date.data = recipe['finish_time']
    seform.finish_time.data = recipe['finish_time']
    seform.solve_for_start.data = "1"

    logger.debug(f"End of create_start_finish_forms(), returning seform: {seform}")
    return seform
