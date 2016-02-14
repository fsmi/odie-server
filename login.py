#! /usr/bin/env python3

from functools import wraps
from flask import request, session

from config import AUTH_COOKIE
from odie import ClientError
from db.fsmi import Cookie


def unauthorized():
    raise ClientError("unauthorized", status=401)


def get_user():
    # kiosk Mode is *never* logged in.
    if is_kiosk():
        return None
    cookie = request.cookies.get(AUTH_COOKIE)
    if not cookie:
        return None
    active_session = Cookie.query.filter_by(sid=cookie).first()
    if active_session:
        active_session.refresh()
        return active_session.user

def is_kiosk():
    return session.get('is_kiosk', False)


def login_required(f):
    @wraps(f)
    def wrapped_f(*args, **kwargs):
        user = get_user()
        if user:
            result = f(*args, **kwargs)
            return result
        return unauthorized()
    return wrapped_f
