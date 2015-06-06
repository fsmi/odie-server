#! /usr/bin/env python3

import odie
import config
import json

from flask import request, jsonify
from flask.ext.login import login_user, logout_user, current_user, login_required

from odie import app, db
from apigen import login_required_for_methods, collection_endpoint, instance_endpoint
from models.documents import Lecture, Deposit, Document, Examinant
from models.odie import Order
from models.public import User
from serialization_schemas import OrderLoadSchema, OrderDumpSchema, LectureSchema, LectureDocumentsSchema, DocumentSchema, ExaminantSchema, DepositSchema, PrintJobLoadSchema


@app.route('/api/config')
def get_config():
    return jsonify(config.FS_CONFIG)


@app.route('/api/login', methods=['POST'])
def login():
    if not current_user.is_authenticated():
        try:
            json = request.get_json(force=True)  # ignore Content-Type
            user = User.authenticate(json['username'], json['password'])
            if not user:
                return ("invalid login", 401, [])
            login_user(user)
        except KeyError:
            return ("malformed request", 400, [])
    return jsonify({
            'user': current_user.username,
            'firstName': current_user.first_name,
            'lastName': current_user.last_name
        })


@app.route('/api/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    return "ok"


@app.route('/api/print', methods=['POST'])
@login_required
def print_documents():
    printjob, errors = PrintJobLoadSchema().load(data=request.get_json(force=True))
    if errors:
        return (str(errors), 400, [])
    try:
        documents = [Document.query.get(i) for i in printjob['documents']]
        assert printjob['depositCount'] >= 0
        price = sum(doc.price for doc in documents)
        # round up to next 10 cents
        price = 10 * (price/10 + (1 if price % 10 else 0))

        if config.FlaskConfig.DEBUG:
            print("PRINTING DOCS {docs} FOR {coverText}: PRICE {price} + {depcount} * DEPOSIT".format(
                docs=printjob['documents'],
                coverText=printjob['coverText'],
                price=price,
                depcount=printjob['depositCount']))
        else:
            #  TODO actual implementation of printing and accounting
            print("PC LOAD LETTER")

        return "ok"
    except (ValueError, KeyError):
        return ("malformed request", 400, [])


def dumpSchema(schema, many=False):
    return lambda obj: schema().dumps(obj, many).data


collection_endpoint(
        url='/api/orders',
        serdes={
            'GET': dumpSchema(OrderDumpSchema, many=True),
            'POST': OrderLoadSchema().make_object
        },
        model=Order,
        auth_methods=['GET'])

instance_endpoint(
        url='/api/orders/<int:instance_id>',
        serializer= dumpSchema(OrderDumpSchema),
        model=Order,
        methods=['GET', 'DELETE'],
        auth_methods=['GET', 'DELETE'])


collection_endpoint(
        url='/api/lectures',
        serdes={'GET': dumpSchema(LectureSchema, many=True)},
        model=Lecture)

instance_endpoint(
        url='/api/lectures/<int:instance_id>',
        serializer=dumpSchema(LectureDocumentsSchema),
        model=Lecture)


collection_endpoint(
        url='/api/documents',
        serdes={'GET': dumpSchema(DocumentSchema, many=True)},
        model=Document)


collection_endpoint(
        url='/api/examinants',
        serdes={'GET': dumpSchema(ExaminantSchema, many=True)},
        model=Examinant)


collection_endpoint(
        url='/api/deposits',
        serdes={'GET': dumpSchema(DepositSchema, many=True)},
        model=Deposit,
        auth_methods=['GET'])

instance_endpoint(
        url='/api/deposits/<int:instance_id>',
        model=Deposit,
        methods=['DELETE'],
        auth_methods=['DELETE'])
