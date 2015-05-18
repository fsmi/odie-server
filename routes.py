#! /usr/bin/env python3

import app
import json

from flask import request, jsonify
from flask.ext.login import login_user, logout_user, current_user, login_required

from app import app, db
from apigen import login_required_for_methods, collection_endpoint, instance_endpoint
from models.documents import Lecture, Deposit, Document, Examinant
from models.odie import Order
from models.public import User
from serialization_schemas import OrderLoadSchema, OrderDumpSchema, LectureSchema, LectureDocumentsSchema, DocumentSchema, ExaminantSchema, DepositSchema


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
