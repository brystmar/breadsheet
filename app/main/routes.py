# determines which page(s) to show for each browser request
from app import db
from app.main import bp
from app.main.forms import RecipeForm, StepForm, ThenWaitForm, StartFinishForm
from app.models import Recipe, Step, Difficulty
from datetime import datetime, timedelta
from flask import render_template, flash, redirect, url_for, request, send_from_directory
from os import path
from sqlalchemy.sql import text
from global_logger import glogger
import logging

logger = glogger
logger.setLevel(logging.DEBUG)
now = datetime.utcnow()


# map the desired URL to this function
@bp.route('/breadsheet')
@bp.route('/index')
@bp.route('/')
def index():
    logger.debug("Rendering the homepage.  End of index().")
    recipes = add_recipe_ui_fields(Recipe.query.order_by('id').all())
    return render_template('index.html', title='Breadsheet Recipe Scheduling Tool', recipes=recipes)


@bp.route('/add_recipe', methods=['GET', 'POST'])
def add_recipe():
    logger.debug("Start of add_recipe()")
    rform = RecipeForm()

    if rform.validate_on_submit():
        logger.info("Recipe form submitted.")
        next_id = db.engine.execute(text("SELECT max(id) FROM recipe")).first()[0] + 1
        rdata = Recipe(id=next_id, name=rform.name.data, author=rform.author.data, source=rform.source.data,
                       difficulty=rform.difficulty.data, date_added=datetime.utcnow())
        logger.info("New recipe data: ".format(rdata.__dict__))

        db.session.add(rdata)
        db.session.commit()
        logger.debug("Recipe_id={} successfully added & committed to the db.".format(next_id))

        recipe_id = rdata.id
        logger.debug("Redirecting to the main recipe page.  End of add_recipe().")
        return redirect(url_for('main.recipe') + '?id={}'.format(recipe_id))

    logger.debug("End of add_recipe()")
    return render_template('add_recipe.html', title='Add Recipe', rform=rform)


@bp.route('/Images')
@bp.route('/Resources')
@bp.route('/recipe', methods=['GET', 'POST'])
def recipe():
    logger.debug("Start of recipe(), request method: {}".format(request.method))
    sform = StepForm()
    recipe_id = request.args.get('id') or 1
    sform.recipe_id.data = recipe_id
    logger.debug("Recipe_id: {}".format(recipe_id))

    if recipe_id == 1 and request.args.get('id') != 1:
        logger.info("Error reading the querystring on the /recipe page.")
        logger.debug("Read: {}".format(request.args.get('id')))
        logger.debug("Replaced it with 1.")

    recipe = add_recipe_ui_fields(Recipe.query.filter_by(id=recipe_id).first())
    steps = set_when(Step.query.filter_by(recipe_id=recipe_id).order_by(Step.number).all(), recipe.start_time)
    twforms = create_tw_forms(steps)
    seform = create_start_finish_forms(recipe)

    if sform.validate_on_submit():
        logger.info("Step form submitted.")

        # convert then_wait decimal value to seconds
        then_wait = hms_to_seconds([sform.then_wait_h.data, sform.then_wait_m.data, sform.then_wait_s.data])

        next_id = db.engine.execute(text("SELECT max(id) FROM step")).first()[0] + 1
        sdata = Step(id=next_id, recipe_id=recipe_id, number=sform.number.data, text=sform.text.data,
                     then_wait=then_wait, wait_time_range=sform.wait_time_range.data)
        logger.info("New step data: ".format(sdata.__dict__))

        db.session.add(sdata)
        db.session.commit()
        logger.debug("Step_id={} successfully added & committed to the db.".format(next_id))

        logger.debug("Redirecting to the main recipe page.  End of recipe().")
        return redirect(url_for('main.recipe') + '?id={}'.format(recipe_id))

    elif request.method == 'GET':  # pre-populate the form with the recipe info and any existing steps
        logger.debug("Entering the 'elif' section to pre-populate the form w/recipe info and any existing steps.")

        # increment from the max step number
        max_step = Step.query.filter_by(recipe_id=recipe_id).order_by(Step.number.desc()).first()
        if max_step is None:
            sform.number.data = 1
        else:
            sform.number.data = max_step.number + 1

    logger.debug("Rendering the recipe page.  End of recipe().")
    return render_template('recipe.html', title=recipe.name, recipe=recipe, steps=steps, sform=sform,
                           seform=seform, twforms=twforms)


@bp.route('/favicon.ico')
def favicon():
    logger.debug("The favicon was requested!! :D")
    return send_from_directory(path.join(bp.root_path, 'static'), 'favicon.ico',
                               mimetype='image/vnd.microsoft.icon')


def seconds_to_hms(num):
    """Accepts a number of seconds (int), returns a three-str list: [hours, minutes, seconds].  Because I'm a newbie."""
    logger.debug("Start of seconds_to_hms(), with: {}".format(num))
    if num is None:
        logger.warning("Argument was None.  End of seconds_to_hms(), returning an empty string.")
        return ""
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
            """if len(result[i]) == 1:
                result[i] = '0' + result[i]"""
            i += 1

    logger.debug("End of seconds_to_hms(), returning: {}".format(result))
    return result


def hms_to_seconds(hms):
    """Accepts a three-int list, returns a number of seconds (int).  Again, because I'm a newbie."""
    logger.debug("Start of hms_to_seconds(), with: {}".format(hms))
    if not (isinstance(hms, list) and len(hms) == 3):
        logger.warning("Error in hms_to_seconds function: Invalid input {}.".format(hms))
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

        logger.debug("End of hms_to_seconds(), returning: {}".format(result))
        return result
    except:
        logger.warning("Error in hms_to_seconds function: List values {} cannot be converted to int.".format(hms))
        logger.debug("End of hms_to_seconds(), returning 0")
        return 0


def hms_to_string(data):
    """Convert a list of [hrs, min, sec] to a human-readable string.  Yet again, because I'm a newbie."""
    logger.debug("Start of hms_to_string(), with: {}".format(data))
    result = ''
    if data[0] == '00':
        pass
    else:
        result = '{} hrs'.format(data[0])

    if data[1] == '00' and result != '':
        logger.debug("End of hms_to_string(), returning: {}".format(result))
        return result  # round off the seconds if it's an even number of hours
    elif data[1] == '00' and result == '':
        pass
    elif result == '':
        result += '{} min'.format(data[1])
    else:
        result += ', {} min'.format(data[1])

    if data[2] == '00' and result != '':
        logger.debug("End of hms_to_string(), returning: {}".format(result))
        return result  # round off the seconds if it's an even number of minutes
    elif data[2] == '00' and result == '':
        logger.debug("End of hms_to_string(), returning: {}".format(result))
        return result
    elif result == '':
        result = '{} sec'.format(data[2])
        logger.debug("End of hms_to_string(), returning: {}".format(result))
        return result
    else:
        result += ', {} sec'.format(data[2])

    logger.debug("End of hms_to_string(), returning: {}".format(result))
    return result


def set_when(steps, when):
    """Accepts a list of Step objects, plus the benchmark time, and calculates when each step should begin.

    Also converts raw seconds to a text string, stored in a UI-specific value for 'then_wait'.
    Returns a list of Steps plus a list of forms.
    """
    logger.debug("Start of set_when(), with steps: {s}, when: {w}".format(s=steps, w=when))
    i = 0
    for s in steps:
        logger.debug("Looking at step: {}".format(s.__dict__))
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

    logger.debug("End of set_when(), returning: {}".format(steps))
    return steps


def difficulty_abbrev(abbrev, values):
    """Return the difficulty text from a set of abbreviations."""
    logger.debug("Start of difficulty_abbrev(), with abbrev: {a}, values: {v}".format(a=abbrev, v=values))
    for v in values:
        if v.id == abbrev:
            logger.debug("End of difficulty_abbrev(), returning: {}".format(v.text))
            return v.text

    logger.debug("No matching value found.  End of difficulty_abbrev(), returning: --")
    return "--"


def add_recipe_ui_fields(recipe):
    """Populate the difficulty_ui, date_added_ui, start_time, & finish_time fields."""
    logger.debug("Start of add_recipe_ui_fields() for: {}".format(recipe))
    # total_time = Step.query.filter_by(recipe_id=1).with_entities(func.sum('then_wait'))

    difficulty_values = Difficulty.query.all()
    if isinstance(recipe, list):  # separate handling for lists
        logger.debug("Parsing a list of recipes.")
        for r in recipe:
            logger.debug("Adding UI fields for recipe: {}".format(r.__dict__))
            r = add_recipe_ui_fields(r)
    else:
        recipe.difficulty_ui = difficulty_abbrev(recipe.difficulty, difficulty_values)
        recipe.date_added_ui = recipe.date_added.strftime('%Y-%m-%d %H:%M')
        if recipe.start_time is None:
            recipe.start_time = now
        recipe.start_time = datetime.strptime(str(recipe.start_time), '%Y-%m-%d %H:%M:%S.%f')
        recipe.start_time_ui = dt_ui(recipe.start_time)

        sql = text("SELECT sum(then_wait) FROM step WHERE recipe_id = {}".format(recipe.id))
        recipe.total_time = db.engine.execute(sql).first()[0]
        if recipe.total_time is None:
            recipe.finish_time = recipe.start_time
            recipe.finish_time_ui = recipe.start_time_ui
        else:
            recipe.finish_time = recipe.start_time + timedelta(seconds=recipe.total_time)
            recipe.finish_time_ui = dt_ui(recipe.finish_time)
            recipe.total_time_ui = hms_to_string(seconds_to_hms(recipe.total_time))

    logger.debug("End of add_recipe_ui_fields(), returning: {}".format(recipe))
    return recipe


def dt_ui(dt):
    logger.debug("Start of dt_ui(), with: {}".format(dt))
    st = str(dt)
    output = st[:st.find('.')-3]
    logger.debug("End of dt_ui(), returning: {}".format(output))
    return output


def create_tw_forms(steps):
    """Create a form for the 'then wait...' display for recipe steps, then populate it with data."""
    logger.debug("Start of create_tw_forms(), with: {}".format(steps))

    twforms = []
    for s in steps:
        logger.debug("Looking at step: {}".format(s.__dict__))
        tw = ThenWaitForm()
        tw.step_id = s.id
        tw.then_wait_h.data = s.then_wait_ui[0]
        tw.then_wait_m.data = s.then_wait_ui[1]
        tw.then_wait_s.data = s.then_wait_ui[2]
        tw.then_wait = s.then_wait
        twforms.append(tw)
    logger.debug("End of create_tw_forms(), returning {}".format(twforms))
    return twforms


def create_start_finish_forms(recipe):
    """Set values for the form displaying start & finish times for this recipe."""
    logger.debug("Start of create_start_finish_forms(), for: {}".format(recipe.__dict__))

    seform = StartFinishForm()
    seform.recipe_id.data = recipe.id
    seform.start_date.data = recipe.start_time
    seform.start_time.data = recipe.start_time
    seform.finish_date.data = recipe.finish_time
    seform.finish_time.data = recipe.finish_time
    seform.solve_for_start.data = str(recipe.solve_for_start)

    logger.debug("End of create_start_finish_forms(), returning seform: {}".format(seform))
    return seform
