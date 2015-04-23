#! /usr/bin/env python3

import app
import models.acl as acl

from app import db

class User(db.Model):
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

