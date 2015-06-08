#! /usr/bin/env python3

import config
import serialization_schemas as serdes

from flask import request
from flask.ext.login import login_user, logout_user, current_user, login_required

from odie import app, db, ClientError
from apigen import collection_endpoint, instance_endpoint
from models.documents import Lecture, Deposit, Document, Examinant
from models.odie import Order
from models.public import User


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

def _lectures(documents):
    # gets unique list of lectures associated with list of documents
    # rather inefficient, does O(len(documents)) queries
    lects = []
    for doc in documents:
        lects.extend(Lecture.query.filter(Lecture.documents.contains(doc)).all())
    return list({lect.id: lect for lect in lects}.values())


@app.route('/api/donation', methods=['POST'])
@login_required
def accept_donation():
    donation, errors = serdes.DonationLoadSchema().load(data=request.get_json(force=True))
    if errors:
        raise ClientError(*errors)
    accounting.log_donation(donation['amount'], donation['cash_box'])
    db.session.commit()
    return {}


@app.route('/api/log_erroneous_sale', methods=['POST'])
@login_required
def accept_erroneous_sale():
    donation, errors = serdes.ErroneousSaleLoadSchema().load(data=request.get_json(force=True))
    if errors:
        raise ClientError(*errors)
    accounting.log_erroneous_sale(donation['amount'], current_user, donation['cash_box'])
    db.session.commit()
    return {}


@app.route('/api/print', methods=['POST'])
@login_required
def print_documents():
    printjob, errors = serdes.PrintJobLoadSchema().load(data=request.get_json(force=True))
    if errors:
        raise ClientError(*errors)
    try:
        documents = [Document.query.get(id) for id in printjob['document_ids']]
        assert printjob['deposit_count'] >= 0
        price = sum(doc.price for doc in documents)
        # round up to next 10 cents
        price = 10 * (price/10 + (1 if price % 10 else 0))

        if config.FlaskConfig.DEBUG:
            print("PRINTING DOCS {docs} FOR {coverText}: PRICE {price} + {depcount} * DEPOSIT".format(
                docs=printjob['document_ids'],
                coverText=printjob['coverText'],
                price=price,
                depcount=printjob['deposit_count']))
        else:
            #  TODO actual implementation of printing and accounting
            print("PC LOAD LETTER")

            for _ in range(printjob['deposit_count']):
                dep = Deposit(
                        price=config.FS_CONFIG['DEPOSIT_PRICE'],
                        name=printjob['student_name'],
                        by_user=current_user.first_name + ' ' + current_user.last_name,
                        lectures=_lectures(documents))
                db.session.add(dep)
                accounting.log_deposit(dep, current_user, printjob['cash_box'])
            if documents:
                num_pages = sum(doc.number_of_pages for doc in documents)
                accounting.log_exam_sale(num_pages, price, current_user, printjob['cash_box'])
            db.session.commit()
        return {}
    except (ValueError, KeyError):
        raise ClientError("malformed request")


collection_endpoint(
        url='/api/orders',
        schemas={
            'GET': serdes.OrderDumpSchema,
            'POST': serdes.OrderLoadSchema
        },
        model=Order,
        auth_methods=['GET'])

instance_endpoint(
        url='/api/orders/<int:instance_id>',
        schema=serdes.OrderDumpSchema,
        model=Order,
        methods=['GET', 'DELETE'],
        auth_methods=['GET', 'DELETE'])


collection_endpoint(
        url='/api/lectures',
        schemas={'GET': serdes.LectureSchema},
        model=Lecture)

@app.route('/api/lectures/<int:id>/documents')
def lecture_documents(id):
    lecture = Lecture.query.get(id)
    return serdes.serialize(lecture.documents, serdes.DocumentSchema, many=True)


collection_endpoint(
        url='/api/examinants',
        schemas={'GET': serdes.ExaminantSchema},
        model=Examinant)

@app.route('/api/examinants/<int:id>/documents')
def examinant_documents(id):
    examinant = Examinant.query.get(id)
    return serdes.serialize(examinant.documents, serdes.DocumentSchema, many=True)


collection_endpoint(
        url='/api/documents',
        schemas={'GET': serdes.DocumentSchema},
        model=Document)


collection_endpoint(
        url='/api/deposits',
        schemas={'GET': serdes.DepositSchema},
        model=Deposit,
        auth_methods=['GET'])

instance_endpoint(
        url='/api/deposits/<int:instance_id>',
        model=Deposit,
        methods=['DELETE'],
        auth_methods=['DELETE'])
