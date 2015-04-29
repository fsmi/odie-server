#! /usr/bin/env python3

from functools import partial

from flask import Flask
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.login import LoginManager
from sqlalchemy.dialects import postgres

app = Flask("odie")
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgres:///fsmi'

# TODO change me in production
app.config['SECRET_KEY'] = 'supersikkrit'
app.config['DEBUG'] = True

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.setup_app(app)

# TODO until I've changed the model to use a common declarative_base with the right
# schema, we have to tell it explicitly for every model (see models.py)
# we set them here for proper reuse (and documentation purposes)
odie_table_args = {'schema' : 'odie'}  # things specific to odie: saved carts
documents_table_args = {'schema': 'documents'}
acl_table_args = {'schema' : 'acl'}  # auth credentials
public_table_args = {'schema' : 'public'}  # if we don't explicitly set this we can't create cross-schema aux tables

# sqlalchemy treats columns as nullable by default, which we don't want.
Column = partial(db.Column, nullable=False)
