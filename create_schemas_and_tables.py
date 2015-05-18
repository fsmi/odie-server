#! /usr/bin/env python3


import sqlalchemy
import app

import models.documents
import models.public
import models.odie

from sqlalchemy.schema import CreateSchema
from sqlalchemy.dialects import postgres
from app import db

def createSchema(name, bind=None):
    try:
        engine = db.get_engine(app.app, bind)
        engine.execute(CreateSchema(name))
    except sqlalchemy.exc.ProgrammingError:
        # schema already exists... do nothing
        pass

# these two should kind of be a given, but... you never know.
createSchema('public', 'fsmi')
createSchema('public')

createSchema('acl', 'fsmi')
createSchema('odie')
createSchema('documents')


# due to issues with postgres.ENUM's inherit_schema parameter not finding the
# right db, we need to create all custom types here ahead of time and manually
# specify the right bind.

garfield = db.get_engine(app.app)
postgres.ENUM('mathematics', 'computer science', 'both', name='subject', schema='documents').create(bind=garfield)
postgres.ENUM('official', 'inofficial', 'none', name='solution', schema='documents').create(bind=garfield)
postgres.ENUM('oral', 'written', 'oral reexam', name='type', schema='documents').create(bind=garfield)


# create tables if necessary
db.create_all()
