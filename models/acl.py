#! /usr/bin/env python3

import odie
import config

from odie import db, Column

class Permission(db.Model):
    __tablename__ = 'rechte'
    __table_args__ = config.acl_table_args

    id = Column(db.Integer, name='rechteid', primary_key=True)
    name = Column(db.String(32), name='rechtename')


effective_permissions = db.Table('effektive_benutzer_rechte',
        Column('benutzer_id', db.Integer, db.ForeignKey('public.benutzer.benutzer_id')),
        Column('rechteid', db.Integer, db.ForeignKey('acl.rechte.rechteid')),
        **config.acl_table_args)
