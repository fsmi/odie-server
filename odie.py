#! /usr/bin/env python3

import app
import routes

from flask.ext.restless import APIManager, ProcessingException
from flask.ext.login import current_user

from app import app, db
from models import documents
from models import odie


def auth_preproc(**kw):
    if not current_user.is_authenticated():
        raise ProcessingException(description='Not Authorized', code=401)

manager = APIManager(app, flask_sqlalchemy_db=db)
manager.create_api(documents.Lecture,
        exclude_columns=['documents'])
manager.create_api(documents.Document,
        exclude_columns=['legacy_id', 'file_id'])
manager.create_api(documents.Examinant)
manager.create_api(
        documents.Deposit,
        methods=['GET', 'POST'],
        preprocessors={'GET_SINGLE': [auth_preproc], 'GET_MANY': [auth_preproc], 'POST': [auth_preproc]})
manager.create_api(odie.Cart, methods=['POST', 'GET'])

app.run()
