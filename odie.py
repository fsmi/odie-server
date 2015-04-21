#! /usr/bin/env python3

import app
from app import app, db
from models import documents
from models import odie

from flask.ext.restless import APIManager

manager = APIManager(app, flask_sqlalchemy_db=db)
manager.create_api(documents.Lecture)
manager.create_api(documents.Document)
manager.create_api(documents.Examinant)
manager.create_api(documents.Deposit)
manager.create_api(odie.Cart, methods=['POST', 'GET'])

app.run()
