#! /usr/bin/env python3

import config

from functools import partial

from flask import Flask
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.login import LoginManager

app = Flask("odie")

app.config.from_object('config.FlaskConfig')

if app.config['DEBUG']:
    # allow requests from default broccoli server port
    from flask.ext.cors import CORS
    CORS(app, origins=['http://localhost:4200'], supports_credentials=True)

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.setup_app(app)
def __unauthorized():
    raise ClientError("unauthorized", status=401)
login_manager.unauthorized_handler(__unauthorized)

# sqlalchemy treats columns as nullable by default, which we don't want.
Column = partial(db.Column, nullable=False)


# errors that will be reported to the client
class ClientError(Exception):
    def __init__(self, *errors, status=400):
        super()
        self.errors = errors
        self.status = status
