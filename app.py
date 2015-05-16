#! /usr/bin/env python3

import config
# extend query operators
import jsonquery
import jsonquery_operators

from functools import partial

from flask import Flask
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.login import LoginManager
from sqlalchemy.dialects import postgres

app = Flask("odie")

app.config.from_object('config.FlaskConfig')

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.setup_app(app)


# sqlalchemy treats columns as nullable by default, which we don't want.
Column = partial(db.Column, nullable=False)
