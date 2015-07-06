#! /usr/bin/env python3

# local settings can be put into a file called 'local_config.py'.
# to override the default flask config supplied here, define a class called FlaskConfig
# in local_config.py which inherits from this class.

import os
import tempfile

class FlaskConfig(object):
    SQLALCHEMY_DATABASE_URI = 'postgres:///garfield'  # use garfield for everything by default
    # we also need to access the fsmi db for auth
    SQLALCHEMY_BINDS = {
        'fsmi': 'postgres:///fsmi',
        'garfield': SQLALCHEMY_DATABASE_URI,
    }

    SECRET_KEY = 'supersikkrit'
    DEBUG = True
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024

# things specific to odie: saved orders
odie_table_args = {
    'schema': 'odie',
    'info': {'bind_key': 'garfield'}
}
documents_table_args = {
    'schema': 'documents',
    'info': {'bind_key': 'garfield'}
}

# auth credentials
acl_table_args = {
    'schema' : 'acl',
    'info': {'bind_key': 'fsmi'}
}
public_table_args = {
    'schema' : 'public',  # if we don't explicitly set this we can't create cross-schema aux tables
    'info': {'bind_key': 'fsmi'}
}

FS_CONFIG = {
    'DEPOSIT_PRICE': 500,  # in cents
    'PRICE_PER_PAGE': 3,   # in cents
    'PRINTERS': [
        'emergency',  # ATIS
        'external',   # print for external customer
    ],
    'CASH_BOXES': [
        'Sprechstundenkasse Informatik',
        'Sprechstundenkasse Mathematik',
    ],
}
SUBMISSION_ALLOWED_FILE_EXTENSIONS = ['.pdf']
GARFIELD_ACCOUNTING = False
ITEMS_PER_PAGE = 20
DOCUMENT_DIRECTORY = os.path.join(tempfile.gettempdir(), 'odie')
ADMIN_PANEL_ALLOWED_GROUPS = ['fsusers']
