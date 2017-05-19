#! /usr/bin/env python3
# -*- coding: UTF-8 -*-

# one of two scripts to create the tables, types and schemas necessary for odie.
# Unfortunately we need to split these (nearly identical) scripts due to Flask-SQLAlchemy
# not correctly handling Enum creation when handling multiple databases.
# (See https://gist.github.com/TehMillhouse/fdaffc4b129283633b37 for an example
# and keep an eye on https://github.com/mitsuhiko/flask-sqlalchemy/pull/222 to see
# whether this is still necessary)

try:
    import hack
except:
    from scripts import hack

import config

# dirty monkey-patching to prevent Flask-SQLA in this script from seeing more
# than one database
uri = config.FlaskConfig.SQLALCHEMY_BINDS['garfield']
config.FlaskConfig.SQLALCHEMY_BINDS = {'garfield': uri}
config.FlaskConfig.SQLALCHEMY_DATABASE_URI = uri

import sqlalchemy
import db.garfield  # pylint: disable=unused-import
import db.documents  # pylint: disable=unused-import
import db.odie  # pylint: disable=unused-import

from sqlalchemy.schema import CreateSchema
from odie import sqla, app
from db.documents import Lecture

def createSchema(name, bind=None):
    try:
        engine = sqla.get_engine(app, bind)
        engine.execute(CreateSchema(name))
    except sqlalchemy.exc.ProgrammingError as e:
        # schema probably already exists... do nothing
        # but just in case it's another error, print it
        print("Error creating schema {}, ignoring: {}".format(name, e))

createSchema('public')
createSchema('odie')
createSchema('garfield')
createSchema('documents')

sqla.create_all()

# create stored procedure for early document rewards
try:
    engine = sqla.get_engine(app,None)
    for call in Lecture.early_document_until_stored_procedure_calls:
        engine.execute(call)
except sqlalchemy.exc.ProgrammingError as e:
        print("Error creating stored procedure, ignoring: {}".format(e))

