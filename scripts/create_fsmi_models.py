#! /usr/bin/env python3

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
uri = config.FlaskConfig.SQLALCHEMY_BINDS['fsmi']
config.FlaskConfig.SQLALCHEMY_BINDS = {'fsmi': uri}
config.FlaskConfig.SQLALCHEMY_DATABASE_URI = uri

import sqlalchemy

from sqlalchemy.schema import CreateSchema
from odie import sqla, app

def createSchema(name, bind=None):
    try:
        engine = sqla.get_engine(app, bind)
        engine.execute(CreateSchema(name))
    except sqlalchemy.exc.ProgrammingError:
        # schema already exists... do nothing
        pass

createSchema('public')
createSchema('acl')

sqla.create_all()
