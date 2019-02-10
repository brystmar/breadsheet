# when connecting from a web browser, show the Hello World page
from app import app

# map the top-level URL to this function
@app.route('/')
# also map the /index URL to this same function
@app.route('/index')

# specify what to return
def index():
    text = '<h1><b>Breadsheet Central</b></h1>'
    text += 'Determine the right schedule for FWSY recipes'
    text += '</br>'
    text += '<div label="recipelist"><p>'
    text += '<ul>'
    text += '<li>Country Sourdough: <i>Pain de Campagne</i></li>'
    text += '<li>Overnight Poolish</li>'
    text += '<li>Saturday White Loaf</li>'
    text += '<li>Pizza Dough</li>'
    text += '</ul>'
    text += '</p></div>'
    return text
