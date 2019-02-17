# when connecting from a web browser, show the Hello World page
from flask import render_template, flash, redirect, url_for, request
from werkzeug.urls import url_parse
from datetime import datetime, timedelta
from random import randint

from app import breadapp, db
from app.forms import RecipeForm, StepForm
from app.models import Recipe, Step


# map the desired URL to this function
@breadapp.route('/')
@breadapp.route('/index')
@breadapp.route('/breadsheet')
def index():
    recipes = Recipe.query.order_by('id').all()

    return render_template('index.html', title='Breadsheet Home', recipes=recipes)


@breadapp.route('/recipe')
def view_recipe():
    recipe_id = request.args.get('id') or 1
    recipe = Recipe.query.filter_by(id=recipe_id).all()[0]
    steps = Step.query.filter_by(recipe_id=recipe_id).order_by(Step.number).all()

    # determine when the next step should begin
    i=0
    when = datetime.now()
    for s in steps:
        if i == 0:
            s.when = when.strftime('%Y-%m-%d %H:%M')
        else:
            s.when = (when + timedelta(minutes=s.then_wait)).strftime('%Y-%m-%d %H:%M')
            when += timedelta(minutes=s.then_wait)
        i += 1

    return render_template('steps.html', title='View Recipe', recipe=recipe, steps=steps)


@breadapp.route('/add_recipe', methods=['GET', 'POST'])
def add_recipe():
    rform = RecipeForm()

    if rform.validate_on_submit():
        rdata = Recipe(name=rform.name.data, author=rform.author.data, source=rform.source.data, difficulty=rform.difficulty.data)
        db.session.add(rdata)
        db.session.commit()

        recipe_id = rdata.id
        flash('Added recipe ' + rform.name.data + '[{}]'.format(recipe_id))

        return redirect(url_for('add_step') + '?id={}'.format(recipe_id))

    return render_template('add_recipe.html', title='Add Recipe', rform=rform)


@breadapp.route('/add_step', methods=['GET', 'POST'])
def add_step():
    recipe_id = request.args.get('id')
    step_id = request.args.get('step_id')
    sform = StepForm()

    recipe = Recipe.query.filter_by(id=recipe_id).all()[0]
    steps = Step.query.filter_by(recipe_id=recipe_id).order_by(Step.number).all()

    if sform.validate_on_submit():
        sdata = Step(recipe_id=recipe_id, number=sform.number.data, text=sform.text.data, then_wait=sform.then_wait.data,
                     wait_time_range=sform.wait_time_range.data)
        db.session.add(sdata)
        db.session.commit()

        step_id = sdata.id
        flash('Step #{} added'.format(sform.number.data, step_id))

        return redirect(url_for('add_step') + '?id={}&step_id={}'.format(recipe_id, step_id))

    elif request.method == 'GET':  # pre-populate the form with the recipe info and any existing steps
        sform.recipe_id.data = recipe_id

        # if step_id != None:
        #    sform.number.data = db.query(Step)

    return render_template('add_step.html', title='Add Step', recipe=recipe, steps=steps, sform=sform)
