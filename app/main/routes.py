"""Determine which page(s) to render for each browser request."""

from app import db, logger
from app.functions import generate_new_id, calculate_recipe_length, add_recipe_ui_fields, cleanup_before_db_write
from app.functions import hms_to_seconds, set_when, create_tw_forms, create_start_finish_forms
from app.main import bp
from app.main.forms import RecipeForm, StepForm, paprika_recipe_ids
from app.models import Recipe, Step, Replacement
from datetime import datetime
from flask import render_template, redirect, url_for, request, send_from_directory  # , flash
from os import path
# from data import recipes_static


# Map the specified URL to this function
@bp.route('/breadsheet')
@bp.route('/index')
@bp.route('/')
def index():
    logger.info("\n\nStart of index()\n\n")

    # Grab all recipes from the db, sort by id
    recipes = sorted(Recipe.scan(), key=lambda r: r.id)

    for each_recipe in recipes:
        # each_recipe = convert_recipe_strings_to_datetime(each_recipe)
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
    failsafe_id = '1560122083.005019_af4f7bd5-ed86-44a2-9767-11f761160dee'  # Detroit pizza
    recipe_id = request.args.get('id') or failsafe_id

    form = StepForm()
    logger.debug(f"Recipe_id from the URL querystring: {recipe_id}")

    if recipe_id == failsafe_id and request.args.get('id') != failsafe_id:
        logger.warning("Error reading the querystring on the /recipe page.")
        logger.debug(f"Read this value: {request.args.get('id')}")
        logger.debug(f"Replaced it with the Detroit pizza recipe id: {recipe_id}")

    # Retrieve the recipe using the URL querystring's id
    recipe_shown = Recipe.query(recipe_id)

    # recipe_shown = convert_recipe_strings_to_datetime(recipe_shown)
    recipe_shown = calculate_recipe_length(recipe_shown)
    recipe_shown = add_recipe_ui_fields(recipe_shown)

    # Optimize the step data for display
    steps = set_when(recipe.steps, recipe.start_time)
    twforms = create_tw_forms(steps)
    seform = create_start_finish_forms(recipe)

    if form.validate_on_submit():
        logger.info("StepForm submitted.")

        # convert the 'then_wait' inputs to seconds
        new_step = Step(number=len(steps) + 1, text=form.text.data,
                        then_wait=hms_to_seconds([form.then_wait_h.data, form.then_wait_m.data, 0]),
                        note=form.note.data if form.note.data != "" else " ")

        logger.info(f"New step data: {new_step}")

        # Add this new step to the existing list of steps
        recipe.steps.append(new_step)

        # Update the database
        Recipe.save(recipe)
        logger.info(f"Recipe {recipe.id} updated in the db to include step {new_step.number}.")

        logger.debug("Redirecting to the main recipe page.  End of recipe().")
        return redirect(url_for("main.recipe") + f"?id={recipe_id}")

    elif request.method == 'GET':
        logger.debug(f"Entering the 'elif' section to pre-populate the add_step form with the "
                     f"next logical step number: {len(steps) + 1}")
        form.number.data = len(steps) + 1

    logger.debug("Rendering the recipe page.  End of recipe().")
    return render_template('recipe.html', title=recipe.name, recipe=recipe, steps=steps, sform=form,
                           seform=seform, twforms=twforms, paprika_recipe_ids=paprika_recipe_ids)


@bp.route('/favicon.ico')
def favicon():
    logger.info("The favicon was requested!! :D")
    return send_from_directory(path.join(bp.root_path, 'static'), 'favicon.ico', mimetype='image/vnd.microsoft.icon')
