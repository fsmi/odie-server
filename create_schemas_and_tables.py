#! /usr/bin/env python3


import sqlalchemy
import app

from sqlalchemy.schema import CreateSchema
from app import db

def createSchema(name):
    try:
        db.engine.execute(CreateSchema(name))
    except sqlalchemy.exc.ProgrammingError:
        # schema already exists... do nothing
        pass

createSchema('acl')
createSchema('odie')
createSchema('documents')

# create tables if necessary
db.create_all()
