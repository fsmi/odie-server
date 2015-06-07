#! /usr/bin/env python3

import config

from flask import request
from flask.ext.login import login_user, logout_user, current_user, login_required

from odie import app, ClientError
from apigen import collection_endpoint, instance_endpoint
from models.documents import Lecture, Deposit, Document, Examinant
from models.odie import Order
from models.public import User
from serialization_schemas import serialize, OrderLoadSchema, OrderDumpSchema, LectureSchema, DocumentSchema, ExaminantSchema, DepositSchema, PrintJobLoadSchema


@app.route('/api/config')
def get_config():
    return config.FS_CONFIG


@app.route('/api/login', methods=['POST'])
def login():
    if not current_user.is_authenticated():
        try:
            json = request.get_json(force=True)  # ignore Content-Type
            user = User.authenticate(json['username'], json['password'])
            if not user:
                raise ClientError("invalid login", status=401)
            login_user(user)
        except KeyError:
            raise ClientError("malformed request")
    return {
            'user': current_user.username,
            'firstName': current_user.first_name,
            'lastName': current_user.last_name
        }


@app.route('/api/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    return {}


@app.route('/api/print', methods=['POST'])
@login_required
def print_documents():
    printjob, errors = PrintJobLoadSchema().load(data=request.get_json(force=True))
    if errors:
        raise ClientError(*errors)
    try:
        documents = [Document.query.get(id) for id in printjob['document_ids']]
        assert printjob['depositCount'] >= 0
        price = sum(doc.price for doc in documents)
        # round up to next 10 cents
        price = 10 * (price/10 + (1 if price % 10 else 0))

        if config.FlaskConfig.DEBUG:
            print("PRINTING DOCS {docs} FOR {coverText}: PRICE {price} + {depcount} * DEPOSIT".format(
                docs=printjob['document_ids'],
                coverText=printjob['coverText'],
                price=price,
                depcount=printjob['depositCount']))
        else:
            #  TODO actual implementation of printing and accounting
            print("PC LOAD LETTER")

        return {}
    except (ValueError, KeyError):
        raise ClientError("malformed request")


collection_endpoint(
        url='/api/orders',
        schemas={
            'GET': OrderDumpSchema,
            'POST': OrderLoadSchema
        },
        model=Order,
        auth_methods=['GET'])

instance_endpoint(
        url='/api/orders/<int:instance_id>',
        schema=OrderDumpSchema,
        model=Order,
        methods=['GET', 'DELETE'],
        auth_methods=['GET', 'DELETE'])


collection_endpoint(
        url='/api/lectures',
        schemas={'GET': LectureSchema},
        model=Lecture)

@app.route('/api/lectures/<int:id>/documents')
def lecture_documents(id):
    lecture = Lecture.query.get(id)
    return serialize(lecture.documents, DocumentSchema, many=True)


collection_endpoint(
        url='/api/examinants',
        schemas={'GET': ExaminantSchema},
        model=Examinant)

@app.route('/api/examinants/<int:id>/documents')
def examinant_documents(id):
    examinant = Examinant.query.get(id)
    return serialize(examinant.documents, DocumentSchema, many=True)


collection_endpoint(
        url='/api/documents',
        schemas={'GET': DocumentSchema},
        model=Document)


collection_endpoint(
        url='/api/deposits',
        schemas={'GET': DepositSchema},
        model=Deposit,
        auth_methods=['GET'])

instance_endpoint(
        url='/api/deposits/<int:instance_id>',
        model=Deposit,
        methods=['DELETE'],
        auth_methods=['DELETE'])
