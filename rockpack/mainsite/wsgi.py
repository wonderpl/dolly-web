from werkzeug.contrib.fixers import ProxyFix
from rockpack.mainsite import app, init_app

init_app()

app.wsgi_app = ProxyFix(app.wsgi_app)

application = app
