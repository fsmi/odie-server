#! /usr/bin/env python3


import sqlalchemy
import app

from sqlalchemy.schema import CreateSchema
from app import db

def createSchema(name, bind=None):
    try:
        engine = db.get_engine(app.app, bind)
        engine.execute(CreateSchema(name))
    except sqlalchemy.exc.ProgrammingError:
        # schema already exists... do nothing
        pass

createSchema('acl', 'fsmi')
createSchema('odie')
createSchema('documents')

# create tables if necessary
db.create_all()
