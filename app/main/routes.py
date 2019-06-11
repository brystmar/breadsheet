"""Determine which page(s) to render for each browser request."""
from app import db, logger
from app.main import bp
from app.main.forms import RecipeForm, StepForm, ThenWaitForm, StartFinishForm, paprika_recipe_ids
from boto3.dynamodb.conditions import Key
from config import PST
from datetime import datetime, timedelta
from flask import render_template, redirect, url_for, request, send_from_directory  # , flash
from os import path


# Map the specified URL to this function
@bp.route('/breadsheet')
@bp.route('/index')
@bp.route('/')
def index():
    logger.info("Start of index()")

    # Grab all recipes from the db
    response = db.Table('Recipe').scan()

    # Check the response code
    response_code = response['ResponseMetadata']['HTTPStatusCode']
    logger.debug(f"Scanned the Recipe table, HTTPStatusCode={response_code}")
    if response_code == 200:
        logger.debug(f"Recipes returned from dynamodb: {response['Items']}")
    else:
        logger.warning(f"DynamoDB error: HTTPStatusCode={response_code}")
        logger.debug(f"Full response log:\n{response['ResponseMetadata']}")

    # Optimize the data for processing & display
    recipes = sort_list_of_dictionaries(response['Items'], 'id')
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
            'start_time':   PST.localize(datetime.now()).strftime("%Y-%m-%d %H:%M:%S"),
            'steps':        [],
            'length':       0
            }

        logger.info(f"New recipe data: {new_recipe}")

        # Write this new recipe to the db
        write_response = db.Table("Recipe").put_item(Item=new_recipe)

        # Check the response code
        response_code = write_response['ResponseMetadata']['HTTPStatusCode']
        if response_code == 200:
            logger.info("Recipe successfully added to the db.")
        else:
            logger.warning(f"DynamoDB error: HTTPStatusCode={response_code}")
            logger.debug(f"Full response log:\n{write_response['ResponseMetadata']}")

        logger.debug("Redirecting to the main recipe page.  End of add_recipe().")
        return redirect(url_for("main.recipe") + f"?id={new_recipe['id']}")

    logger.debug("End of add_recipe()")
    return render_template('add_recipe.html', title='Add Recipe', rform=form)


@bp.route('/Images')
@bp.route('/Resources')
@bp.route('/recipe', methods=['GET', 'POST'])
def recipe():
    logger.info(f"Start of recipe(), request method: {request.method}")

    # Read the recipe_id from the URL querystring
    failsafe_id = '1560122083.005019_af4f7bd5-ed86-44a2-9767-11f761160dee'  # Detroit pizza
    recipe_id = request.args.get('id') or failsafe_id

    form = StepForm()
    logger.debug(f"Recipe_id from the URL querystring: {recipe_id}")

    if recipe_id == failsafe_id and request.args.get('id') != failsafe_id:
        logger.warning("Error reading the querystring on the /recipe page.")
        logger.debug(f"Read: {request.args.get('id')}")
        logger.debug(f"Replaced it with the Detroit pizza recipe id: {recipe_id}")

    # Retrieve the recipe using the URL querystring's id
    response = db.Table('Recipe').query(KeyConditionExpression=Key('id').eq(recipe_id))

    # Check the response code
    response_code = response['ResponseMetadata']['HTTPStatusCode']
    logger.debug(f"Scanned the Recipe table, HTTPStatusCode={response_code}")
    if response_code == 200:
        logger.debug(f"Recipe returned from dynamodb: {response['Items'][0]}")
    else:
        logger.warning(f"DynamoDB error: HTTPStatusCode={response_code}")
        logger.debug(f"Full response log:\n{response['ResponseMetadata']}")

    # Optimize the recipe data for processing & display
    recipe = convert_recipe_strings_to_datetime(response['Items'][0])
    recipe = calculate_recipe_length(recipe)
    recipe = add_recipe_ui_fields(recipe)

    # Optimize the step data for display
    steps = set_when(recipe['steps'], recipe['start_time'])
    twforms = create_tw_forms(steps)
    seform = create_start_finish_forms(recipe)

    if form.validate_on_submit():
        logger.info("StepForm submitted.")

        # convert the 'then_wait' inputs to seconds
        new_step = {
            'number': len(steps) + 1,
            'text': form.text.data,
            'then_wait': hms_to_seconds([form.then_wait_h.data, form.then_wait_m.data, 0]),
            'note': form.note.data if form.note.data != "" else " "
        }
        logger.info(f"New step data: {new_step}")

        # Add this new step to the existing list of steps
        recipe['steps'].append(new_step)

        # Update the database
        write_response = db.Table("Recipe").put_item(Item=cleanup_before_db_write(recipe))

        # Check the response code
        response_code = write_response['ResponseMetadata']['HTTPStatusCode']
        if response_code == 200:
            logger.info("Recipe successfully added to the db.")
        else:
            logger.warning(f"DynamoDB error: HTTPStatusCode={response_code}")
            logger.debug(f"Full response log:\n{write_response['ResponseMetadata']}")

        logger.info(f"Recipe {recipe['id']} updated in the db to include step {new_step['number']}.")

        logger.debug("Redirecting to the main recipe page.  End of recipe().")
        return redirect(url_for('main.recipe') + f'?id={recipe_id}')

    elif request.method == 'GET':
        logger.debug(f"Entering the 'elif' section to pre-populate the add_step form with the "
                     f"next logical step number: {len(steps) + 1}")
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


def cleanup_before_db_write(recipe_input):
    """Additional attributes are added to recipes & steps for easier local processing.  No need to add these to the db.

    Also, DynamoDB doesn't accept datetime objects in string fields, so we need to convert those fields to strings."""
    logger.debug(f"Entering cleanup_before_db_write(), with: {recipe_input}")

    # Remove unnecessary attributes
    recipe_fields_to_remove = ['start_time_ui', 'start_time_split', 'date_added_ui', 'total_time', 'total_time_ui',
                               'finish_time', 'finish_time_ui']
    step_fields_to_remove = ['when', 'then_wait_ui', 'then_wait_list', 'then_wait_timedelta']

    for r in recipe_fields_to_remove:
        result = recipe_input.pop(r, None)

        if result is not None:
            # Only returns a non-null value if something was removed
            logger.debug(f"Removed recipe item: {r}")

    for step in recipe_input['steps']:
        for s in step_fields_to_remove:
            result = step.pop(s, None)

            if result is not None:
                logger.debug(f"Removed step #{step['number']} item: {s}")

    # Convert datetime objects to strings
    recipe_input['date_added'] = recipe_input['date_added'].strftime('%Y-%m-%d')
    recipe_input['start_time'] = recipe_input['start_time'].strftime('%Y-%m-%d %H:%M:%S')

    logger.debug(f"End of cleanup_before_db_write(), with: {recipe_input}")
    return recipe_input


def convert_recipe_strings_to_datetime(recipe_input):
    """Most recipe fields are stored as strings in the db.  Convert them to datetime objects here."""
    logger.debug(f"Start of convert_recipe_strings_to_datetime() for {len(recipe_input)} recipe_input(s)")

    # Makes this function recursive if the input was a list
    if isinstance(recipe_input, list):
        logger.debug(f"Parsing a list of {len(recipe_input)} recipes.")
        for r in recipe_input:
            r = convert_recipe_strings_to_datetime(r)
    else:
        logger.debug(f"Converting fields for recipe_input {recipe_input['id']}: {recipe_input['name']}")
        recipe_input['date_added'] = datetime.strptime(recipe_input['date_added'], '%Y-%m-%d')

        # TODO: Make these lines unnecessary!
        recipe_input['start_time'] = PST.localize(datetime.now())
        recipe_input['start_time_ui'] = recipe_input['start_time'].strftime('%Y-%m-%d %H:%M:%S')

        # Length comes in as type=Decimal; some functions only accept integers
        try:
            recipe_input['length'] = int(recipe_input['length'])
        except KeyError:
            recipe_input['length'] = calculate_recipe_length(recipe_input)

    logger.debug(f"End of convert_recipe_strings_to_datetime()")
    return recipe_input


def calculate_recipe_length(recipe_input):
    """Add/update the recipe_input's length (in seconds) by summing the length of each step."""
    logger.debug(f"Start of calculate_recipe_length() for recipe_input {recipe_input['id']}")
    try:
        original_length = recipe_input['length']
    except KeyError:
        original_length = -1

    length = 0
    for step in recipe_input['steps']:
        if isinstance(step['then_wait'], timedelta):
            length += int(step['then_wait'].total_seconds())  # total_seconds returns a float
        else:
            length += step['then_wait']

    logger.debug(f"Calculated length: {length}, original length: {original_length}")
    recipe_input['length'] = length

    if length != original_length:
        # Update the database if the length changed
        write_response = db.Table("Recipe").put_item(Item=cleanup_before_db_write(recipe_input))

        # Check the response code
        response_code = write_response['ResponseMetadata']['HTTPStatusCode']
        if response_code == 200:
            logger.info("Recipe successfully added to the db.")
        else:
            logger.warning(f"DynamoDB error: HTTPStatusCode={response_code}")
            logger.debug(f"Full response log:\n{write_response['ResponseMetadata']}")

        logger.info(f"Updated recipe_input {recipe_input['id']} in the database to reflect its new length.")

    logger.debug("End of calculate_recipe_length()")
    return recipe_input


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
    if data[0] in('0', '00'):
        pass
    elif data[0] == '1':
        result = f'{data[0]} hr'
    else:
        result = f'{data[0]} hrs'

    if data[1] in('0', '00') and result != '':
        logger.debug(f"End of hms_to_string(), returning: {result}")
        return result  # round off the seconds if it's an even number of hours
    elif data[1] in('0', '00') and result == '':
        pass
    elif result == '':
        result += f'{data[1]} min'
    else:
        result += f', {data[1]} min'

    # No need to display seconds
    # if data[2] in('0', '00') and result != '':
    #     logger.debug(f"End of hms_to_string(), returning: {result}")
    #     return result  # round off the seconds if it's an even number of minutes
    # elif data[2] in('0', '00') and result == '':
    #     logger.debug(f"End of hms_to_string(), returning: {result}")
    #     return result
    # elif result == '':
    #     result = f'{data[2]} sec'
    #     logger.debug(f"End of hms_to_string(), returning: {result}")
    #     return result
    # else:
    #     result += f', {data[2]} sec'

    logger.debug(f"End of hms_to_string(), returning: {result}")
    return result


def set_when(steps, when) -> list:
    """Calculate when each step should begin, using a list of steps plus the benchmark time. Returns a list of steps."""

    logger.debug(f"Start of set_when(), with when={when}, {len(steps)} steps, all steps: {steps}")
    i = 0
    for s in steps:
        logger.debug(f"Looking at step {s['number']}, when={when.strftime('%a %H:%M')}, then_wait={s['then_wait']}")

        # Set the 'when' for this step
        s['when'] = when.strftime('%a %H:%M')

        # Create a timedelta object for then_wait to simplify formulas
        s['then_wait'] = 0 if s['then_wait'] is None else int(s['then_wait'])
        s['then_wait_timedelta'] = timedelta(seconds=s['then_wait'])

        # Increment
        when += s['then_wait_timedelta']

        s['then_wait_ui'] = str(s['then_wait_timedelta'])
        s['then_wait_list'] = s['then_wait_ui'].split(":")
        i += 1

        logger.debug(f"Finished step {s['number']}: then_wait={s['then_wait']}, timedelta={s['then_wait_timedelta']}, "
                     f"tw_ui={s['then_wait_ui']}, tw_list={s['then_wait_list']}, when={when} (aka next step)")

    logger.debug(f"End of set_when(), returning: {steps}")
    return steps


def add_recipe_ui_fields(recipe_input):
    """Input: an individual Recipe class, or a list of Recipes.

    Populates the date_added_ui, start_time, & finish_time fields."""
    logger.debug(f"Start of add_recipe_ui_fields() for {len(recipe_input)} recipe_input(s)")

    # Makes this function recursive if the input was a list
    if isinstance(recipe_input, list):
        logger.debug(f"Parsing a list of {len(recipe_input)} recipes.")
        for r in recipe_input:
            r = add_recipe_ui_fields(r)
    else:
        logger.debug(f"Adding UI fields for recipe_input {recipe_input['id']}: {recipe_input['name']}")
        recipe_input['date_added_ui'] = str(recipe_input['date_added'])[:10]

        # Ensure start_time is a timedelta object
        if not isinstance(recipe_input['start_time'], datetime):
            recipe_input['start_time'] = datetime.strptime(recipe_input['start_time'], '%Y-%m-%d %H:%M:%S')

        if recipe_input['length'] in (None, 0):
            recipe_input['finish_time'] = recipe_input['start_time']
            recipe_input['finish_time_ui'] = recipe_input['start_time_ui']
            recipe_input['length'] = 0
        else:
            delta_length = timedelta(seconds=int(recipe_input['length']))
            recipe_input['finish_time'] = recipe_input['start_time'] + delta_length
            recipe_input['finish_time_ui'] = recipe_input['finish_time'].strftime('%Y-%m-%d %H:%M:%S')

            if 'day' in str(delta_length):
                # If the recipe_input takes >24hrs, the system formats the string: '2 days, 1:30:05'
                delta_length_split = str(delta_length).split(", ")
                delta_to_parse = delta_length_split[1].split(':')
                recipe_input['total_time_ui'] = f"{delta_length_split[0]}, {hms_to_string(delta_to_parse)}"
            else:
                recipe_input['total_time_ui'] = hms_to_string(str(delta_length).split(':'))

    logger.debug(f"End of add_recipe_ui_fields()")
    return recipe_input


def create_tw_forms(steps) -> list:
    """Create a form for the 'then wait...' display for recipe steps, then populate it with data."""
    logger.debug(f"Start of create_tw_forms(), with: {steps}")

    twforms = []
    for s in steps:
        logger.debug(f"Looking at step {s['number']}, then_wait={s['then_wait']}, then_wait_ui={s['then_wait_ui']}")
        tw = ThenWaitForm()
        tw.step_number = s['number']

        # If steps take >24hrs, timedelta strings are formatted: '2 days, 1:35:28'
        if 'day' in s['then_wait_ui']:
            # Split the string into days, then everything else
            days = int(s['then_wait_ui'].split(" day")[0])
            # days = days // (60 * 60 * 24)

            # Split the second portion by ':', then add the number of hours
            hours = int(s['then_wait_list'][1]) + (days * 24)
            tw.then_wait_m.data = s['then_wait_list'][2]
        else:
            # Otherwise, just split as normal
            hours = s['then_wait_list'][0]
            tw.then_wait_m.data = s['then_wait_list'][1]

        # timedelta doesn't zero-pad the hours, so F* IT! WE'LL DO IT LIVE!
        if int(hours) <= 9:
            tw.then_wait_h.data = "0" + str(hours)
        else:
            tw.then_wait_h.data = str(hours)

        tw.then_wait = s['then_wait']
        logger.debug(f"Done w/{s['number']}: then_wait_h={tw.then_wait_h.data}, then_wait_m={tw.then_wait_m.data}")
        twforms.append(tw)
    logger.debug(f"End of create_tw_forms(), returning {twforms}")
    return twforms


def create_start_finish_forms(recipe_input) -> StartFinishForm:
    """Set values for the form displaying start & finish times for this recipe."""
    logger.debug(f"Start of create_start_finish_forms(), for {recipe_input['id']}")

    seform = StartFinishForm()
    seform.recipe_id.data = recipe_input['id']
    seform.start_date.data = recipe_input['start_time']
    seform.start_time.data = recipe_input['start_time']
    seform.finish_date.data = recipe_input['finish_time']
    seform.finish_time.data = recipe_input['finish_time']
    seform.solve_for_start.data = "1"

    logger.debug(f"End of create_start_finish_forms(), returning seform: {seform}")
    return seform
