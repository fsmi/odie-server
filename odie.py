#! /usr/bin/env python3

import config

from functools import partial, wraps

from flask import Flask, jsonify
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

# uniform response formatting:
# {"data": <jsonified route result>}
# or {"errors": <errors>} on ClientError
def __route(*args, **kwargs):
    def decorator(f):
        @wraps(f)
        def wrapped_f(*f_args, **f_kwargs):
            try:
                return jsonify(data=f(*f_args, **f_kwargs))
            except ClientError as e:
                return (jsonify(errors=e.errors), e.status, [])
        return Flask.route(app, *args, **kwargs)(wrapped_f)
    return decorator
app.route = __route
