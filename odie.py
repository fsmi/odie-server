#! /usr/bin/env python3

from functools import partial
import logging

from flask import Flask
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.login import LoginManager

app = Flask("odie", template_folder='admin/templates', static_folder='admin/static')

import config  # pylint: disable=unused-import
app.config.from_object('config.FlaskConfig')

if app.debug:
    # allow requests from default broccoli server port
    from flask.ext.cors import CORS
    CORS(app, origins=['http://localhost:4200'], supports_credentials=True)
else:
    # production logger to stderr
    handler = logging.StreamHandler()
    handler.setLevel(logging.INFO)
    handler.setFormatter(logging.Formatter('[%(asctime)s] %(levelname)s in %(module)s: %(message)s'))
    app.logger.addHandler(handler)

sqla = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.setup_app(app)
def __unauthorized():
    raise ClientError("unauthorized", status=401)
login_manager.unauthorized_handler(__unauthorized)

# sqlalchemy treats columns as nullable by default, which we don't want.
Column = partial(sqla.Column, nullable=False)


# errors that will be reported to the client
class ClientError(Exception):
    def __init__(self, *errors, status=400):
        super().__init__()
        self.errors = errors
        self.status = status
