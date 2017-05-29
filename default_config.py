#! /usr/bin/env python3

# local settings can be put into a file called 'local_config.py'.
# to override the default flask config supplied here, define a class called FlaskConfig
# in local_config.py which inherits from this class.

import os
import tempfile
import time

from flask import session
from marshmallow.utils import missing

def print_documents(doc_paths: list, cover_text: str, printer: str, user: str, usercode: int, job_title: str):
    from odie import app
    app.logger.info("Printing documents {} ({} in total) on {} for {} [{}|{}|{}]".format(doc_paths, len(doc_paths), printer, cover_text, job_title, user, usercode))
    for _ in doc_paths:
        time.sleep(1)
        yield ()

def document_validated(doc_path: str):
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
    CSRF_COOKIE_NAME = 'csrf_token'  # important for flask-admin compatibility
    DEBUG_TB_INTERCEPT_REDIRECTS = False
    BABEL_DEFAULT_LOCALE = 'de'

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

# (host, port)
# Why is the port number duplicated? Because it's happened in the past that multiple
# scanners were connected to one pc, with that pc running multiple instances of
# barcodescannerd
LASER_SCANNERS = {
    'FSI': [
        ('fsi-pc5', 3974),
        ('fsi-pc0', 3974),
        ('fsi-pc4', 3974),
    ],
    'FSM': [
        ('fsm-pc5', 3974),
    ],
}
FS_CONFIG = {
    'LOGIN_PAGE': '/login',
    'LOGOUT_URL': '/logout',
    'DEPOSIT_PRICE': 500,  # in cents
    'PRICE_PER_PAGE': 3,   # in cents
    'EARLY_DOCUMENT_REWARD': 500, # in cents
    'EARLY_DOCUMENT_COUNT': 5, # number of documents counting as early (https://www.fsmi.uni-karlsruhe.de/Fachschaft/Sitzungen/ProtokollAnzeigen.html?protokoll_id=849)
    'EARLY_DOCUMENT_EXTRA_DAYS': 14, # number of days documents count as early, afer the *_COUNT one
    'OFFICES': {
        'FSI': {
            'cash_boxes': ['Sprechstundenkasse Informatik'],
            'printers': ['FSI-Drucker', 'ATIS-Notdrucker'],
            'scanners': [],  # initialized when barcode module is imported
        },
        'FSM': {
            'cash_boxes': ['Sprechstundenkasse Mathematik'],
            'printers': ['FSM-Drucker', 'Tisch-Drucker'],
            'scanners': [],  # initialized when barcode module is imported
        }
    },
    'IS_KIOSK': None # set by get_config
}
SUBMISSION_ALLOWED_FILE_EXTENSIONS = ['.pdf']
LOCAL_SERVER = True
ITEMS_PER_PAGE = 20
DOCUMENT_DIRECTORY = os.path.join(tempfile.gettempdir(), 'odie')
ADMIN_PANEL_ALLOWED_GROUPS = ['fsusers']
AUTH_COOKIE = 'FSMISESSID'

PRINTER_USERCODES = {'internal': 3974}
for cash_box in FS_CONFIG['OFFICES']['FSI']['cash_boxes']:
    PRINTER_USERCODES[cash_box] = 2222
for cash_box in FS_CONFIG['OFFICES']['FSM']['cash_boxes']:
    PRINTER_USERCODES[cash_box] = 2224


def try_get_office(user):
    return missing

def log_admin_audit(view, model, msg):
    from odie import app

    app.logger.info(msg)
