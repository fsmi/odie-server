#! /usr/bin/env python3

# local settings can be put into a file called 'local_config.py'.
# to override the default flask config supplied here, define a class called FlaskConfig
# in local_config.py which inherits from this class.

class FlaskConfig(object):
    SQLALCHEMY_DATABASE_URI = 'postgres:///garfield'  # use garfield for everything by default
    SQLALCHEMY_BINDS = { 'fsmi': 'postgres:///fsmi' }  # we also need to access the fsmi db for auth

    SECRET_KEY = 'supersikkrit'
    DEBUG = True

# TODO until I've changed the model to use a common declarative_base with the right
# schema, we have to tell it explicitly for every model (see models.py)
# we set them here for proper reuse (and documentation purposes)
odie_table_args = {'schema' : 'odie'}  # things specific to odie: saved carts
documents_table_args = {'schema': 'documents'}


# auth credentials
acl_table_args = {
    'schema' : 'acl',
    'info': {'bind_key': 'fsmi'}
}
public_table_args = {
    'schema' : 'public',  # if we don't explicitly set this we can't create cross-schema aux tables
    'info': {'bind_key': 'fsmi'}
}

DEPOSIT_PRICE = 500  # in cents
PRICE_PER_PAGE = 3   # in cents
