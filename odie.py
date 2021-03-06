#! /usr/bin/env python3

from functools import partial
from datetime import timedelta
import logging

from flask import Flask, session
from flask_babelex import Babel
from flask_sqlalchemy import SQLAlchemy
from flask_seasurf import SeaSurf  # CSRF. Got it?

app = Flask("odie", template_folder='admin/templates', static_folder='admin/static')

import config  # pylint: disable=unused-import
app.config.from_object('config.FlaskConfig')

babel = Babel(app)
csrf = SeaSurf(app)
sqla = SQLAlchemy(app)

@app.before_request
def make_session_permanent():
    # We use flask sessions for remembering which client is in kiosk mode.
    # By default, these sessions expire when the browser is closed. Prevent that.
    session.permanent = True
    app.permanent_session_lifetime = timedelta(days=2*365)  # should be long enough...

if app.debug:
    # allow requests from default broccoli server port
    from flask_cors import CORS
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

from db.fsmi import Cookie

# errors that will be reported to the client
class ClientError(Exception):
    def __init__(self, *errors, status=400):
        super().__init__()
        self.errors = errors
        self.status = status
