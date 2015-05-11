#! /usr/bin/env python3

import app
import config

from app import db

class Permission(db.Model):
    __tablename__ = 'rechte'
    __table_args__ = config.acl_table_args

    id = app.Column(db.Integer, name='rechteid', primary_key=True)
    name = app.Column(db.String(32), name='rechtename')


effective_permissions = db.Table('effektive_benutzer_rechte',
        app.Column('benutzer_id', db.Integer, db.ForeignKey('public.benutzer.benutzer_id')),
        app.Column('rechteid', db.Integer, db.ForeignKey('acl.rechte.rechteid')),
        **config.acl_table_args)
