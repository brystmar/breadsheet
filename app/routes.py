# when connecting from a web browser, show the Hello World page
from flask import render_template, flash, redirect, url_for, request
from werkzeug.urls import url_parse
from datetime import datetime

from app import app, db
from app.forms import RecipeForm, StepForm
from app.models import Recipe, Step


# map the desired URL to this function
@app.route('/')
@app.route('/index')
@app.route('/breadsheet')
def index():
    recipes = [
        {
            'id': 1001,
            'name': 'Default recipe',
            'author': 'Nobody',
            'source': 'My head',
            'difficulty': 'Medium',
            'date_added': datetime.now()
            }
        ]

    return render_template('index.html', title='Breadsheet Home', recipes=recipes)

@app.route('/recipe', methods=['GET', 'POST'])
def recipe():
    form = RecipeForm()

    if form.validate_on_submit():
        db.session.add()
        flash('Recipe added successfully!')


    return render_template('recipe.html', title='Recipe', recipe=recipe)


# @app.route('/recipe/<name>/steps', methods=['GET', 'POST'])
@app.route('/steps', methods=['GET', 'POST'])
def steps():
    steps = StepForm()

    return render_template('steps.html', title='Recipe', steps=steps)


def oldindex():
    text = '<h1>Breadsheet</h1>'
    text += '<h2>h2 text here</h2>'
    text += '<h3>h3 text here</h3>'
    text += '<h4>h4 text here</h4>'
    text += '<h5>h5 text here</h5>'
    text += '<h6>h6 text here</h6>'
    text += 'Determine the right schedule for FWSY recipes'
    text += '</br>'
    text += '<div class="recipelist"><p>'
    text += '<ul>'
    text += '<li>Country Sourdough: <i>Pain de Campagne</i></li>'
    text += '<li>Overnight Poolish</li>'
    text += '<li>Saturday White Loaf</li>'
    text += '<li>Pizza Dough</li>'
    text += '</ul>'
    text += '</p></div>'
    return text