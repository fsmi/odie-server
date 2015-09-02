#! /usr/bin/env python3

from functools import partial
import logging

from flask import Flask
from flask.ext.babelex import Babel
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.login import LoginManager
from flask.ext.seasurf import SeaSurf  # CSRF. Got it?

app = Flask("odie", template_folder='admin/templates', static_folder='admin/static')

import config  # pylint: disable=unused-import
app.config.from_object('config.FlaskConfig')

babel = Babel(app)
csrf = SeaSurf(app)
sqla = SQLAlchemy(app)

if app.debug:
    # allow requests from default broccoli server port
    from flask.ext.cors import CORS
    CORS(app, origins=['http://localhost:4200'], supports_credentials=True)

    import flask_debugtoolbar
    toolbar = flask_debugtoolbar.DebugToolbarExtension(app)
    csrf.exempt(flask_debugtoolbar.panels.sqlalchemy.sql_select)
else:
    # production logger to stderr
    handler = logging.StreamHandler()
    handler.setLevel(logging.INFO)
    handler.setFormatter(logging.Formatter('[%(asctime)s] %(levelname)s in %(module)s: %(message)s'))
    app.logger.setLevel(logging.INFO)
    app.logger.addHandler(handler)

# sqlalchemy treats columns as nullable by default, which we don't want.
Column = partial(sqla.Column, nullable=False)

login_manager = LoginManager()
login_manager.setup_app(app)
def __unauthorized():
    raise ClientError("unauthorized", status=401)
login_manager.unauthorized_handler(__unauthorized)

from db.fsmi import Cookie

@login_manager.request_loader
def load_SSO(request):  # pylint: disable=no-self-argument
    cookie = request.cookies.get('FSMISESSID')
    if not cookie:
        return None
    active_session = Cookie.query.filter_by(sid=cookie).first()
    if active_session:
        active_session.refresh()
        return active_session.user

# In addition to the request loader, we also need a user id based loader.
# This is because flask-login will attempt to set its own session cookie
# and only load users from that as soon as it's present.
# It's theoretically possible to configure flask-login to use our cookie
# and load users from that, but this is simpler. This does mean one superfluous
# cookie, though. *shrug*
@login_manager.user_loader
def load(user_id):
    active_session = Cookie.query.filter_by(user_id=user_id).order_by(Cookie.last_action.desc()).first()
    if active_session:
        active_session.refresh()
        return active_session.user
    return None


# errors that will be reported to the client
class ClientError(Exception):
    def __init__(self, *errors, status=400):
        super().__init__()
        self.errors = errors
        self.status = status
