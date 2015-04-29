#! /usr/bin/env python3

import app
import models.public

from functools import wraps

from app import app
from flask import request
from flask.ext.restless import ProcessingException
from flask.ext.login import login_user, logout_user, current_user, login_required
from models.public import User


@app.route('/api/login', methods=['POST'])
def login():
    try:
        json = request.get_json(force=True)  # ignore Content-Type
        user = User.authenticate(json['username'], json['password'])
        if user:
            login_user(user)
            return ("ok", 200, [])
        raise ProcessingException(description="invalid login", code=401)
    except KeyError:
        raise ProcessingException(description="malformed request", code=400)

@app.route('/api/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    return ("ok", 200, [])
