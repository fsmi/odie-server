#! /usr/bin/env python3

import crypt

from models.public import User

class AuthBackend(object):
    def authenticate(self, username, password):
        user = User.query.filter_by(username=username).first()
        if not user:
            return None

        if user.has_permission('homepage_login') and\
           crypt.crypt(password, user.pw_hash) == user.pw_hash:
            return user
        else:
            return None

    def get_user(self, user_id):
        return User.query.get(user_id)
