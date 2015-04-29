#! /usr/bin/env python3

import crypt

import app
import models.acl as acl

from flask.ext.login import UserMixin
from app import db, login_manager

class User(db.Model, UserMixin):
    __tablename__ = 'benutzer'
    __table_args__ = app.public_table_args

    id = app.Column(db.Integer, name='benutzer_id', primary_key=True)
    username = app.Column(db.String(255), name='benutzername', unique=True)
    first_name = app.Column(db.Text, name='vorname')
    last_name = app.Column(db.Text, name='nachname')
    pw_hash = app.Column(db.String(255), name='passwort')
    effective_permissions = db.relationship('Permission', secondary=acl.effective_permissions, lazy='dynamic')

    @property
    def full_name(self):
        return self.first_name + ' ' + self.last_name

    def has_permission(self, perm_name):
        return self.effective_permissions.filter_by(name=perm_name).first() is not None

    @staticmethod
    def authenticate(username, password):
        user = User.query.filter_by(username=username).first()
        if not user:
            return None
        if user.has_permission('homepage_login') and\
           crypt.crypt(password, user.pw_hash) == user.pw_hash:
            return user
        else:
            return None

    @login_manager.user_loader
    def load(user_id):
        return User.query.get(user_id)
