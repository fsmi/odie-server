#! /usr/bin/env python3

import crypt

import config
import datetime
import db.acl as acl

from flask.ext.login import UserMixin
from odie import sqla, login_manager, Column
from sqlalchemy.sql import column


# In the real database, cookies is a view which automatically handles deleting expired cookies.
# When mapping this, we can just treat it like any other table, though... with a couple of caveats

class Cookie(sqla.Model):
    __tablename__ = 'cookies'
    __table_args__ = config.fsmi_table_args

    sid = Column(sqla.Text, primary_key=True)
    user_id = Column(sqla.Integer, sqla.ForeignKey('public.benutzer.benutzer_id'), name='benutzer_id')
    user = sqla.relationship('User')
    last_action = Column(sqla.DateTime, primary_key=True)
    lifetime = Column(sqla.Integer)

    def refresh(self):
        if not config.LOCAL_SERVER:
            # we can't use an SQL expression for this, because then sqlalchemy will try to fetch the
            # result of that with a RETURNING clause, which doesn't work on this view.
            # If we inform sqlalchemy of all values of the mapped instance by keeping them inside python,
            # it's fine though
            now = datetime.datetime.now()
            sqla.session.add(Cookie(sid=self.sid, user_id=self.user_id, last_action=now, lifetime=self.lifetime))


class User(sqla.Model, UserMixin):
    __tablename__ = 'benutzer'
    __table_args__ = config.fsmi_table_args

    id = Column(sqla.Integer, name='benutzer_id', primary_key=True)
    username = Column(sqla.String(255), name='benutzername', unique=True)
    first_name = Column(sqla.Text, name='vorname')
    last_name = Column(sqla.Text, name='nachname')
    pw_hash = Column(sqla.String(255), name='passwort')
    effective_permissions = sqla.relationship('Permission', secondary=acl.effective_permissions, lazy='dynamic')

    @property
    def full_name(self):
        return self.first_name + ' ' + self.last_name

    def has_permission(self, *perm_names):
        return self.effective_permissions.filter(acl.Permission.name.in_(perm_names)).first() is not None

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

