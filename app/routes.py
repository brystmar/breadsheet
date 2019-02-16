# when connecting from a web browser, show the Hello World page
from flask import render_template, flash, redirect, url_for, request
from werkzeug.urls import url_parse
from datetime import datetime, timedelta
from random import randint

from app import app, db
from app.forms import RecipeForm, StepForm
from app.models import Recipe, Step


# map the desired URL to this function
@app.route('/')
@app.route('/index')
@app.route('/breadsheet')
def index():
    recipes = get_recipe_data()

    return render_template('index.html', title='Breadsheet Home', recipes=recipes)


@app.route('/recipe')
def view_recipe():
    steps = get_step_data()

    # convert db data to strings for tidy display
    for s in steps:
        s['when'] = s['when'].strftime('%Y-%m-%d %H:%M')
        s['then_wait'] = str(s['then_wait']) + ' min'

    return render_template('steps.html', title='View Recipe', recipe=get_recipe_data()[2], steps=steps)


@app.route('/add_recipe', methods=['GET', 'POST'])
def add_recipe():
    rform = RecipeForm()
    sform = StepForm()

    if rform.validate_on_submit():
        rdata = Recipe(name=rform.name.data)
        # db.session.add(rdata)
        # db.session.commit()
        flash('Successfully added ' + rform.name.data)
        return redirect(url_for('index'))

    return render_template('add_recipe.html', title='Add Recipe', rform=rform)


def get_recipe_data():
    recipes = [
        {
            'id':         1001,
            'name':       'Default recipe',
            'author':     'Nobody',
            'source':     'My head',
            'difficulty': 'Easy',
            'date_added': None
        },
        {
            'id':         1002,
            'name':       'New-American Baguettes',
            'author':     'Seattle badasses',
            'source':     'Sea Wolf Bakery',
            'difficulty': 'Medium',
            'date_added': None
        },
        {
            'id':         1003,
            'name':       'FWSY Sourdough (Pain de Campagne)',
            'author':     'Ken Forkish',
            'source':     'Flour Water Salt Yeast',
            'difficulty': 'Hard',
            'date_added': None
        },
        {
            'id':         1004,
            'name':       'Pizza Dough (Napolitana)',
            'author':     'Italian Grandmother',
            'source':     'Cook Like My Bubbie',
            'difficulty': 'Medium',
            'date_added': None
        },
        {
            'id':         1005,
            'name':       'Pizza Dough (Detroit-style)',
            'author':     'Kenji Lopez-Alt',
            'source':     'Serious Eats',
            'difficulty': 'Medium',
            'date_added': None
        }
    ]

    for r in recipes:
        r['date_added'] = datetime.now() - timedelta(days=randint(1, 365 * 2)) - timedelta(seconds=randint(1, 1440 * 60))
        r['date_added'] = r['date_added'].strftime('%Y-%m-%d %H:%M:%S')

    return recipes


def get_step_data():
    steps = [
        {
            'number':           1,
            'text':             'Mix the final dough',
            'when':             None,
            'then_wait':        15,
            'wait_time_range':  '10 to 15 minutes'
        },
        {
            'number':           2,
            'text':             'Fold #1',
            'when':             None,
            'then_wait':        20,
            'wait_time_range':  '15 to 30 minutes'
        },
        {
            'number':           3,
            'text':             'Fold #2',
            'when':             None,
            'then_wait':        20,
            'wait_time_range':  '15 to 30 minutes'
        },
        {
            'number':           4,
            'text':             'Fold #3, then cover',
            'when':             None,
            'then_wait':        0,
            'wait_time_range':  None
        },
        {
            'number':           5,
            'text':             'Final rise',
            'when':             None,
            'then_wait':        245,
            'wait_time_range':  '~5 hours after mixing'
        },
        {
            'number':           6,
            'text':             'Preheat the oven to 500F',
            'when':             None,
            'then_wait':        45,
            'wait_time_range':  '35 to 50 minutes'
        },
        {
            'number':           7,
            'text':             'Bake!',
            'when':             None,
            'then_wait':        50,
            'wait_time_range':  '45 to 55 minutes'
        },
        {
            'number':           8,
            'text':             'Remove from oven and cool on wire rack',
            'when':             None,
            'then_wait':        30,
            'wait_time_range':  '~30 minutes'
        }
    ]

    i=0
    for s in steps:
        if i == 0:
            s['when'] = datetime.now()
        else:
            s['when'] = steps[i-1]['when'] + timedelta(minutes=s['then_wait'])
        i += 1

    return steps
