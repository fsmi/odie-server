#! /usr/bin/env python3

# local settings can be put into a file called 'local_config.py'.
# to override the default flask config supplied here, define a class called FlaskConfig
# in local_config.py which inherits from this class.

import os
import tempfile
from marshmallow.utils import missing

def print_documents(doc_paths: list, cover_text: str, printer: str):
    print("Docs %s for %s on %s" % (str(doc_paths), cover_text, printer))

def document_validated(document):
    # on the production server, this triggers prerendering the pdf as pcl5
    pass

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
    STATIC_FOLDER = 'admin/static'

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
fsmi_table_args = {
    'schema' : 'public',  # if we don't explicitly set this we can't create cross-schema aux tables
    'info': {'bind_key': 'fsmi'}
}

FS_CONFIG = {
    'DEPOSIT_PRICE': 500,  # in cents
    'PRICE_PER_PAGE': 3,   # in cents
    'OFFICES': {
        'FSI': {
            'cash_boxes': ['Sprechstundenkasse Informatik'],
            'printers': ['FSI-Drucker', 'ATIS-Notdrucker'],
        },
        'FSM': {
            'cash_boxes': ['Sprechstundenkasse Mathematik'],
            'printers': ['FSM-Drucker']
        }
    }
}
SUBMISSION_ALLOWED_FILE_EXTENSIONS = ['.pdf']
GARFIELD_ACCOUNTING = False
ITEMS_PER_PAGE = 20
DOCUMENT_DIRECTORY = os.path.join(tempfile.gettempdir(), 'odie')
ADMIN_PANEL_ALLOWED_GROUPS = ['fsusers']

def try_get_office(user):
    return missing
