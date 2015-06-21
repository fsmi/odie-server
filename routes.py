#! /usr/bin/env python3

import accounting
import api_utils
import config
import serialization_schemas as schemas

from flask import request
from flask.ext.login import login_user, logout_user, current_user, login_required

from odie import app, db, ClientError
from api_utils import endpoint, filtered_results, api_route
from models.documents import Lecture, Deposit, Document, Examinant
from models.odie import Order
from models.public import User


@api_route('/api/config')
def get_config():
    return config.FS_CONFIG


@api_route('/api/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if not current_user.is_authenticated():
            (obj, errors) = schemas.UserLoadSchema().load(request.get_json(force=True))
            if errors:
                raise ClientError(*errors)
            user = User.authenticate(obj['username'], obj['password'])
            if user:
                login_user(user)
    if not current_user.is_authenticated():
        raise ClientError('permission denied', status=401)

    return schemas.serialize(current_user, schemas.UserDumpSchema)


@api_route('/api/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    return {}

def _lectures(document_ids):
    return Lecture.query.filter(Lecture.documents.any(
        Document.id.in_(document_ids))).all()


@api_route('/api/print', methods=['POST'])
@api_utils.deserialize(schemas.PrintJobLoadSchema)
@login_required
def print_documents(data):
    documents = [Document.query.get(id) for id in data['document_ids']]  # TODO sort documents in python
    assert data['deposit_count'] >= 0
    price = sum(doc.price for doc in documents)
    # round up to next 10 cents
    price = 10 * (price/10 + (1 if price % 10 else 0))

    if config.FlaskConfig.DEBUG:
        print("PRINTING DOCS {docs} FOR {cover_text}: PRICE {price} + {depcount} * DEPOSIT".format(
            docs=data['document_ids'],
            cover_text=data['cover_text'],
            price=price,
            depcount=data['deposit_count']))
    else:
        #  TODO actual implementation of printing
        print("PC LOAD LETTER")

        for _ in range(data['deposit_count']):
            dep = Deposit(
                    price=config.FS_CONFIG['DEPOSIT_PRICE'],
                    name=data['student_name'],
                    by_user=current_user.full_name,
                    lectures=_lectures(data['document_ids']))
            db.session.add(dep)
            accounting.log_deposit(dep, current_user, data['cash_box'])
        if documents:
            num_pages = sum(doc.number_of_pages for doc in documents)
            accounting.log_exam_sale(num_pages, price, current_user, data['cash_box'])
        db.session.commit()
    return {}


@api_route('/api/log_erroneous_sale', methods=['POST'])
@login_required
@api_utils.deserialize(schemas.ErroneousSaleLoadSchema)
def accept_erroneous_sale(data):
    accounting.log_erroneous_sale(data['amount'], current_user, data['cash_box'])
    db.session.commit()
    return {}


@api_route('/api/log_deposit_return', methods=['POST'])
@login_required
@api_utils.deserialize(schemas.DepositLoadSchema)
def log_deposit_return(data):
    dep = Deposit.query.get(data['id'])
    db.session.delete(dep)
    accounting.log_deposit_return(dep, current_user, data['cash_box'])
    db.session.commit()
    return {}


@api_route('/api/donation', methods=['POST'])
@login_required
@api_utils.deserialize(schemas.DonationLoadSchema)
def log_donation(data):
    accounting.log_donation(data['amount'], data['cash_box'])
    db.session.commit()
    return {}


api_route('/api/orders', methods=['GET'])(
login_required(
api_utils.endpoint(
        schemas={
            'GET': schemas.OrderDumpSchema,
            'POST': schemas.OrderLoadSchema
        },
        query=Order.query)
))

api_route('/api/orders', methods=['POST'])(
api_utils.endpoint(
        schemas={
            'POST': schemas.OrderLoadSchema
        },
        query=Order.query)
)

api_route('/api/orders/<int:instance_id>', methods=['GET', 'DELETE'])(
login_required(
api_utils.endpoint(
        schemas={'GET': schemas.OrderDumpSchema},
        query=Order.query,
        allow_delete=True)
))


api_route('/api/lectures')(
api_utils.endpoint(
        schemas={'GET': schemas.LectureSchema},
        query=Lecture.query)
)

@api_route('/api/lectures/<int:id>/documents')
def lecture_documents(id):
    lecture = Lecture.query.get(id)
    return api_utils.filtered_results(lecture.documents, schemas.DocumentSchema)


api_route('/api/examinants')(
api_utils.endpoint(
        schemas={'GET': schemas.ExaminantSchema},
        query=Examinant.query)
)

@api_route('/api/examinants/<int:id>/documents')
def examinant_documents(id):
    examinant = Examinant.query.get(id)
    return api_utils.filtered_results(examinant.documents, schemas.DocumentSchema)

api_route('/api/documents')(
api_utils.endpoint(
        schemas={'GET': schemas.DocumentSchema},
        query=Document.query)
)

api_route('/api/deposits')(
login_required(
api_utils.endpoint(
        schemas={'GET': schemas.DepositDumpSchema},
        query=Deposit.query)
))
