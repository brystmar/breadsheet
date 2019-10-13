"""Determine which page(s) to render for each browser request."""

import json
from app import logger
from app.main import bp
from app.main.forms import RecipeForm, StepForm, ThenWaitForm, StartFinishForm, paprika_recipe_ids
from app.models import Recipe, Step, Replacement
from config import Config
from datetime import datetime, timedelta
from flask import render_template, redirect, url_for, request, send_from_directory  # , flash
from os import path
from pynamodb.attributes import ListAttribute
from pynamodb.exceptions import ScanError, TableDoesNotExist


# Map the specified URL to this function
@bp.route('/')
@bp.route('/index')
@bp.route('/breadsheet')
def index():
    logger.info("\n\nStart of breadsheet index()\n\n")

    # Grab all recipes from the db, sort by id
    recipes = Recipe.scan()
    recipes = sorted(recipes, key=lambda r: r.id)

    logger.info("Rendering the homepage.  End of index()")
    return render_template('index.html', title='Breadsheet: A Recipe Scheduling Tool', recipes=recipes)


@bp.route('/add_recipe', methods=['GET', 'POST'])
def add_recipe():
    logger.info("Start of add_recipe()")

    form = RecipeForm()
    if form.validate_on_submit():
        logger.info("RecipeForm submitted.")

        now = datetime.utcnow()

        # Use the form data submitted to create an instance of the Recipe class
        new_recipe = Recipe(id=generate_new_id(),
                            name=form.name.data,
                            author=form.author.data,
                            source=form.source.data,
                            difficulty=form.difficulty.data,
                            date_added=now,
                            start_time=now,
                            steps=[],
                            length=0)

        # Write this new recipe to the db
        logger.info(f"Writing new recipe {new_recipe.__repr__()} to the database.")
        new_recipe.save()
        logger.info(f"Database write successful.")

        logger.debug("Redirecting to the main recipe page.  End of add_recipe().")
        return redirect(url_for("main.recipe") + f"?id={new_recipe.id}")

    logger.debug("End of add_recipe()")
    return render_template('add_recipe.html', title='Add Recipe', rform=form)


@bp.route('/recipe', methods=['GET', 'POST'])
def recipe():
    logger.info(f"Start of recipe(), request method: {request.method}")

    # Read the recipe_id from the URL querystring
    failsafe_id = '1560122083.005019'  # Detroit-style pizza dough
    recipe_id = request.args.get('id') or failsafe_id

    form = StepForm()
    logger.debug(f"Recipe_id from the URL querystring: {recipe_id}")

    if recipe_id == failsafe_id and request.args.get('id') != failsafe_id:
        logger.warning("Error reading the querystring on the /recipe page.")
        logger.warning(f"Read this value: {request.args.get('id')}; replaced with the Detroit Pizza id: {recipe_id}")

    # Retrieve the recipe using the URL querystring's id
    recipe_shown = Recipe.get(recipe_id)
    logger.debug(f"Recipe retrieved: {recipe_shown.name} ({recipe_shown.id})")

    recipe_shown.update_length()

    # Optimize the step data for display
    recipe_shown.steps = set_when(recipe_shown.steps, recipe_shown.start_time)
    twforms = create_tw_forms(recipe_shown.steps)
    seform = create_start_finish_forms(recipe_shown)

    if form.validate_on_submit():
        logger.info("StepForm submitted.")

        # Create a new Step class for the submitted data
        new_step = Step(number=len(recipe_shown.steps) + 1,
                        text=form.text.data,
                        then_wait=form.then_wait_s,
                        note=form.note.data)
        logger.info(f"New step #{new_step.number} added.")

        # Add this new step to the existing list of steps
        recipe_shown.steps.append(new_step)

        # Update the database
        recipe_shown.save()
        logger.info(f"Recipe {recipe_shown.name} updated in the db to include step {new_step.number}.")

        logger.debug("Redirecting to the main recipe page.  End of recipe().")
        return redirect(url_for("main.recipe") + f"?id={recipe_id}")

    elif request.method == 'GET':
        # When the page loads, pre-populate the add_step form with the next logical step number
        form.number.data = len(recipe_shown.steps) + 1

    logger.debug("Rendering the recipe page.  End of recipe().")
    return render_template('recipe.html', title=recipe_shown.name, recipe=recipe_shown, steps=recipe_shown.steps,
                           sform=form, seform=seform, twforms=twforms, paprika_recipe_ids=paprika_recipe_ids)


@bp.route('/get_single_recipe')
def get_single_recipe(recipe_id) -> json:
    """Given an id, return the requested recipe as a serialized JSON string."""
    # Input validation
    if not isinstance(recipe_id, str):
        return {
            'Status': '400',
            'Details': {
                'ErrorType': TypeError,
                'Message': 'RecipeId must be a string.'
            }
        }
    
    elif recipe_id == "":
        return {
            'Status': '400',
            'Details': {
                'ErrorType': ValueError,
                'Message': 'RecipeId cannot be an empty string.'
            }
        }

    try:
        output = Recipe.get(recipe_id)
        return {
            'Status': '200',
            'Details': {
                'Data': output.dumps(),
                'Message': 'Success!'
            }
        }

    except Recipe.DoesNotExist as e:
        return {
            'Status': '404',
            'Details': {
                'Error': str(e),
                'ErrorType': Recipe.DoesNotExist,
                'Message': 'Invalid recipe id.'
            }
        }


@bp.route('/get_all_recipes')
def get_all_recipes() -> json:
    """Returns a list of JSON objects, representing every recipe in the database."""

    try:
        recipes = Recipe.scan()
        output = []
        for r in recipes:
            output.append(r.dumps())

        return {
            'Status': '200',
            'Details': {
                'Data': output,
                'Message': 'Success!'
            }
        }

    except ScanError as e:
        return {
            'Status': '400',
            'Details': {
                'Error': str(e),
                'ErrorType': ScanError,
                'Message': 'Scan error on the Recipe table.'
            }
        }

    except TableDoesNotExist as e:
        return {
            'Status': '404',
            'Details': {
                'Error': str(e),
                'ErrorType': TableDoesNotExist,
                'Message': 'Recipe table does not exist.'
            }
        }


@bp.route('/get_replacements_data')
def get_replacements_data() -> json:
    """Returns all replacements data."""

    try:
        reps = Replacement.scan()
        return {
            'Status': '200',
            'Details': {
                'Data': reps.next().dumps(),
                'Message': 'Success!'
            }
        }

    except ScanError as e:
        return {
            'Status': '400',
            'Details': {
                'Error': str(e),
                'ErrorType': ScanError,
                'Message': 'Scan error on the Replacement table.'
            }
        }

    except TableDoesNotExist as e:
        return {
            'Status': '404',
            'Details': {
                'Error': str(e),
                'ErrorType': TableDoesNotExist,
                'Message': 'Replacement table does not exist.'
            }
        }


@bp.route('/favicon.ico')
def favicon():
    logger.info("Favicon was requested!! :D")
    return send_from_directory(path.join(bp.root_path, 'static'), 'favicon.ico', mimetype='image/vnd.microsoft.icon')


def generate_new_id() -> str:
    """Primary key (id) is a 17-digit epoch timestamp.  Ex: 1560043140.168794"""
    # For sanity, ensure all ids are the same length.  Timestamps occasionally end in 0, which the system truncates.
    new_id = ""
    while len(new_id) != 17:
        new_id = str(datetime.utcnow().timestamp())
    return new_id


def set_when(steps: ListAttribute(), when: datetime) -> Recipe.steps:
    """Calculate when each step should begin, using a list of steps plus the benchmark time.  Return a list of steps."""
    logger.debug(f"Start of set_when(), with when={when}, {len(steps)} steps, all steps: {steps}")
    i = 0
    for step in steps:
        logger.debug(f"Looking at step {step.number}, when={when.strftime('%Y-%m-%d %H:%M:%S')}, "
                     f"then_wait={step.then_wait}")

        # Set the 'when' for this step
        step.when = when.strftime('%Y-%m-%d %H:%M:%S')

        # Create a timedelta object for then_wait to simplify formulas
        step.then_wait = 0 if step.then_wait is None else int(step.then_wait)

        # Increment
        when += timedelta(seconds=step.then_wait)

        step.then_wait_ui = str(timedelta(seconds=step.then_wait))
        i += 1

        logger.debug(f"Finished step {step.number}")

    logger.debug(f"End of set_when(), returning: {steps}")
    return steps


def create_tw_forms(steps: ListAttribute()) -> list:
    """Create a form for the 'then wait...' display for recipe steps, then populate it with data."""
    logger.debug(f"Start of create_tw_forms(), with: {steps}")

    twforms = []
    for step in steps:
        logger.debug(f"Looking at step {step.number}, then_wait={step.then_wait}, then_wait_ui={step.then_wait_ui}")
        tw = ThenWaitForm()
        tw.step_number = step.number
        split = step.then_wait_ui.split(":")

        # If steps take >24hrs, timedelta strings are formatted: '2 days, 1:35:28'
        if 'day' in step.then_wait_ui:
            # Split the string into days, then everything else
            days = int(step.then_wait_ui.split(" day")[0])
            # days = days // (60 * 60 * 24)

            # Split the second portion by ':', then add the number of hours
            hours = int(split[1]) + (days * 24)
            tw.then_wait_m.data = split[2]
        else:
            # Otherwise, just split as normal
            hours = split[0]
            tw.then_wait_m.data = split[1]

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


def create_start_finish_forms(recipe_input: Recipe) -> StartFinishForm:
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
