#! /usr/bin/env python3

import app
import json

from functools import wraps

from app import app, db
from flask import request, jsonify
from flask.ext.restless import ProcessingException
from flask.ext.login import login_user, logout_user, current_user, login_required
from models.public import User


@app.route('/api/login', methods=['POST'])
def login():
    if current_user.is_authenticated():
        return jsonify({
                'user': current_user.username,
                'firstName': current_user.first_name,
                'lastName': current_user.last_name
            })
    try:
        json = request.get_json(force=True)  # ignore Content-Type
        user = User.authenticate(json['username'], json['password'])
        if user:
            login_user(user)
            return jsonify({
                    'user': user.username,
                    'firstName': user.first_name,
                    'lastName': user.last_name
                })
        raise ProcessingException(description="invalid login", code=401)
    except KeyError:
        raise ProcessingException(description="malformed request", code=400)


@app.route('/api/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    return ("ok", 200, [])
