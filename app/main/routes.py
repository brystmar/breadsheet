"""Determine which page(s) to render for each browser request."""

from app import db, logger
from app.functions import generate_new_id, hms_to_seconds, hms_to_string
from app.main import bp
from app.main.forms import RecipeForm, StepForm, ThenWaitForm, StartFinishForm, paprika_recipe_ids
from app.models import Recipe, Step
from config import Config
from datetime import datetime, timedelta
from flask import render_template, redirect, url_for, request, send_from_directory  # , flash
from os import path


# Map the specified URL to this function
@bp.route('/breadsheet')
@bp.route('/index')
@bp.route('/')
def index():
    logger.info("\n\nStart of index()\n\n")

    # Grab all recipes from the db, sort by id
    recipes = Recipe.scan()
    recipes = sorted(recipes, key=lambda r: r.id)

    for each_recipe in recipes:
        each_recipe = add_recipe_ui_fields(each_recipe)

    logger.info("Rendering the homepage.  End of index()")
    return render_template('index.html', title='Breadsheet: A Recipe Scheduling Tool', recipes=recipes)


@bp.route('/add_recipe', methods=['GET', 'POST'])
def add_recipe():
    logger.info("Start of add_recipe()")

    form = RecipeForm()
    if form.validate_on_submit():
        logger.info("RecipeForm submitted.")

        # Use the form data submitted to create an instance of the Recipe class
        new_recipe = Recipe(id=generate_new_id(),
                            name=form.name.data,
                            author=form.author.data,
                            source=form.source.data,
                            difficulty=form.difficulty.data,
                            date_added=datetime.utcnow(),
                            start_time=datetime.utcnow(),
                            steps=[],
                            length=0)

        logger.info(f"New recipe data: {new_recipe}")

        # Write this new recipe to the db
        Recipe.save(new_recipe)

        logger.debug("Redirecting to the main recipe page.  End of add_recipe().")
        return redirect(url_for("main.recipe") + f"?id={new_recipe.id}")

    logger.debug("End of add_recipe()")
    return render_template('add_recipe.html', title='Add Recipe', rform=form)


@bp.route('/recipe', methods=['GET', 'POST'])
def recipe():
    logger.info(f"Start of recipe(), request method: {request.method}")

    # Read the recipe_id from the URL querystring
    failsafe_id = '1560122083.005019_af4f7bd5-ed86-44a2-9767-11f761160dee'  # Detroit-style pizza dough
    recipe_id = request.args.get('id') or failsafe_id

    form = StepForm()
    logger.debug(f"Recipe_id from the URL querystring: {recipe_id}")

    if recipe_id == failsafe_id and request.args.get('id') != failsafe_id:
        logger.warning("Error reading the querystring on the /recipe page.")
        logger.warning(f"Read this value: {request.args.get('id')}; replaced with the Detroit Pizza id: {recipe_id}")

    # Retrieve the recipe using the URL querystring's id
    recipe_shown = Recipe.query(recipe_id).next()
    logger.debug(f"Recipe retrieved: {recipe_shown.name} ({recipe_shown.id})")

    recipe_shown = calculate_recipe_length(recipe_shown)
    recipe_shown = add_recipe_ui_fields(recipe_shown)

    # Optimize the step data for display
    recipe_shown.steps = set_when(recipe_shown.steps, recipe_shown.start_time)
    twforms = create_tw_forms(recipe_shown.steps)
    seform = create_start_finish_forms(recipe_shown)

    if form.validate_on_submit():
        logger.info("StepForm submitted.")

        # convert the 'then_wait' inputs to seconds
        new_step = Step(number=len(recipe_shown.steps) + 1, text=form.text.data,
                        then_wait=hms_to_seconds([form.then_wait_h.data, form.then_wait_m.data, 0]),
                        note=form.note.data if form.note.data != "" else " ")
        logger.info(f"New step data: {new_step}")

        # Add this new step to the existing list of steps
        recipe.steps.append(new_step)

        # Update the database
        Recipe.save(recipe)
        logger.info(f"Recipe {recipe.name} updated in the db to include step {new_step.number}.")

        logger.debug("Redirecting to the main recipe page.  End of recipe().")
        return redirect(url_for("main.recipe") + f"?id={recipe_id}")

    elif request.method == 'GET':
        logger.debug(f"Entering the 'elif' section to pre-populate the add_step form with the "
                     f"next logical step number: {len(recipe_shown.steps) + 1}")
        form.number.data = len(recipe_shown.steps) + 1

    logger.debug("Rendering the recipe page.  End of recipe().")
    return render_template('recipe.html', title=recipe_shown.name, recipe=recipe_shown, steps=recipe_shown.steps,
                           sform=form, seform=seform, twforms=twforms, paprika_recipe_ids=paprika_recipe_ids)


@bp.route('/favicon.ico')
def favicon():
    logger.info("The favicon was requested!! :D")
    return send_from_directory(path.join(bp.root_path, 'static'), 'favicon.ico', mimetype='image/vnd.microsoft.icon')


def calculate_recipe_length(recipe_input):
    """Add/update the recipe_input's length (in seconds) by summing the length of each step."""
    logger.debug(f"Start of calculate_recipe_length() for {recipe_input.name}")
    try:
        original_length = recipe_input.length
    except KeyError:
        original_length = -1

    length = 0
    for step in recipe_input.steps:
        if isinstance(step.then_wait, timedelta):
            length += int(step.then_wait.total_seconds())  # total_seconds returns a float
        else:
            length += step.then_wait

    logger.debug(f"Calculated length: {length}, original length: {original_length}")
    recipe_input.length = length

    if length != original_length:
        # Update the database if the length changed
        write_response = db.Table("Recipe").put_item(Item=recipe_input)

        # Check the response code
        response_code = write_response['ResponseMetadata']['HTTPStatusCode']
        if response_code == 200:
            logger.info("Recipe successfully added to the db.")
        else:
            logger.warning(f"DynamoDB error: HTTPStatusCode={response_code}")
            logger.debug(f"Full response log:\n{write_response['ResponseMetadata']}")

        logger.info(f"Updated recipe {recipe_input.name} in the database to reflect its new length.")

    logger.debug("End of calculate_recipe_length()")
    return recipe_input


def set_when(steps, when) -> Recipe.steps:
    """Calculate when each step should begin, using a list of steps plus the benchmark time. Returns a list of steps."""
    logger.debug(f"Start of set_when(), with when={when}, {len(steps)} steps, all steps: {steps}")
    i = 0
    for step in steps:
        logger.debug(f"Looking at step {step.number}, when={when.strftime(Config.step_when_format)}, "
                     f"then_wait={step.then_wait}")

        # Set the 'when' for this step
        step.when = when.strftime(Config.step_when_format)

        # Create a timedelta object for then_wait to simplify formulas
        step.then_wait = 0 if step.then_wait is None else int(step.then_wait)

        # Increment
        when += timedelta(seconds=step.then_wait)

        step.then_wait_ui = str(timedelta(seconds=step.then_wait))
        step.then_wait_list = step.then_wait_ui.split(":")
        i += 1

        logger.debug(f"Finished step {step.number}")

    logger.debug(f"End of set_when(), returning: {steps}")
    return steps


def add_recipe_ui_fields(recipe_input) -> Recipe:
    """Input: an individual Recipe class.  Populates date_added_ui, start_time, finish_time, & total_time_ui."""
    logger.debug(f"Start of add_recipe_ui_fields() for {recipe_input.name}")

    if recipe_input.length in (None, 0, "", " "):
        recipe_input.finish_time = recipe_input.start_time
        recipe_input.finish_time_ui = recipe_input.start_time_ui
        recipe_input.length = 0
    else:
        delta_length = timedelta(seconds=int(recipe_input.length))
        recipe_input.finish_time = recipe_input.start_time + delta_length
        recipe_input.finish_time_ui = recipe_input.finish_time.strftime(Config.datetime_format)

        if 'day' in str(delta_length):
            # If the recipe_input takes >24hrs, the system formats the string: '2 days, 1:30:05'
            delta_length_split = str(delta_length).split(", ")
            delta_to_parse = delta_length_split[1].split(':')
            recipe_input.total_time_ui = f"{delta_length_split[0]}, {hms_to_string(delta_to_parse)}"
        else:
            recipe_input.total_time_ui = hms_to_string(str(delta_length).split(':'))

    logger.debug(f"End of add_recipe_ui_fields()")
    return recipe_input


def create_tw_forms(steps) -> list:
    """Create a form for the 'then wait...' display for recipe steps, then populate it with data."""
    logger.debug(f"Start of create_tw_forms(), with: {steps}")

    twforms = []
    for step in steps:
        logger.debug(f"Looking at step {step.number}, then_wait={step.then_wait}, then_wait_ui={step.then_wait_ui}")
        tw = ThenWaitForm()
        tw.step_number = step.number

        # If steps take >24hrs, timedelta strings are formatted: '2 days, 1:35:28'
        if 'day' in step.then_wait_ui:
            # Split the string into days, then everything else
            days = int(step.then_wait_ui.split(" day")[0])
            # days = days // (60 * 60 * 24)

            # Split the second portion by ':', then add the number of hours
            hours = int(step.then_wait_list[1]) + (days * 24)
            tw.then_wait_m.data = step.then_wait_list[2]
        else:
            # Otherwise, just split as normal
            hours = step.then_wait_list[0]
            tw.then_wait_m.data = step.then_wait_list[1]

        # timedelta doesn't zero-pad the hours, so F* IT! WE'LL DO IT LIVE!
        if int(hours) <= 9:
            tw.then_wait_h.data = "0" + str(hours)
        else:
            tw.then_wait_h.data = str(hours)

        tw.then_wait = step.then_wait
        logger.debug(f"Done w/{step.number}: then_wait_h={tw.then_wait_h.data}, then_wait_m={tw.then_wait_m.data}")
        twforms.append(tw)
    logger.debug(f"End of create_tw_forms(), returning {twforms}")
    return twforms


def create_start_finish_forms(recipe_input) -> StartFinishForm:
    """Set values for the form displaying start & finish times for this recipe."""
    logger.debug(f"Start of create_start_finish_forms() for {recipe_input.name}")

    seform = StartFinishForm()
    seform.recipe_id.data = recipe_input.id
    seform.start_date.data = recipe_input.start_time
    seform.start_time.data = recipe_input.start_time
    seform.finish_date.data = recipe_input.finish_time
    seform.finish_time.data = recipe_input.finish_time
    seform.solve_for_start.data = "1"

    logger.debug(f"End of create_start_finish_forms(), returning seform: {seform}")
    return seform
