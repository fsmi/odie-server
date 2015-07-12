#! /usr/bin/env python3

import config

from odie import sqla, Column

class Permission(sqla.Model):
    __tablename__ = 'rechte'
    __table_args__ = config.acl_table_args

    id = Column(sqla.Integer, name='rechteid', primary_key=True)
    name = Column(sqla.String(32), name='rechtename')


effective_permissions = sqla.Table('effektive_benutzer_rechte',
        Column('benutzer_id', sqla.Integer, sqla.ForeignKey('public.benutzer.benutzer_id')),
        Column('rechteid', sqla.Integer, sqla.ForeignKey('acl.rechte.rechteid')),
        **config.acl_table_args)
