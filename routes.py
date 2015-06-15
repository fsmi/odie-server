#! /usr/bin/env python3

import accounting
import apigen
import config
import serialization_schemas as schemas

from flask import request
from flask.ext.login import login_user, logout_user, current_user, login_required

from odie import app, db, ClientError
from models.documents import Lecture, Deposit, Document, Examinant
from models.odie import Order
from models.public import User


@app.route('/api/config')
def get_config():
    return config.FS_CONFIG


@app.route('/api/login', methods=['POST'])
def login():
    if not current_user.is_authenticated():
        (obj, errors) = schemas.UserLoadSchema().load(request.get_json(force=True))
        if errors:
            raise ClientError(*errors)
        user = User.authenticate(obj['username'], obj['password'])
        if not user:
            raise ClientError("invalid login", status=401)
        login_user(user)
    return apigen.serialize(current_user, schemas.UserDumpSchema)


@app.route('/api/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    return {}

def _lectures(document_ids):
    return Lecture.query.filter(Lecture.documents.any(
        Document.id.in_(document_ids))).all()


@app.route('/api/print', methods=['POST'])
@apigen.deserialize(schemas.PrintJobLoadSchema)
@login_required
def print_documents(data):
    documents = [Document.query.get(id) for id in data['document_ids']]  # TODO sort documents in python
    assert data['deposit_count'] >= 0
    price = sum(doc.price for doc in documents)
    # round up to next 10 cents
    price = 10 * (price/10 + (1 if price % 10 else 0))

    if config.FlaskConfig.DEBUG:
        print("PRINTING DOCS {docs} FOR {coverText}: PRICE {price} + {depcount} * DEPOSIT".format(
            docs=data['document_ids'],
            coverText=data['coverText'],
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


@app.route('/api/log_erroneous_sale', methods=['POST'])
@login_required
@apigen.deserialize(schemas.ErroneousSaleLoadSchema)
def accept_erroneous_sale(data):
    accounting.log_erroneous_sale(data['amount'], current_user, data['cash_box'])
    db.session.commit()
    return {}


@app.route('/api/log_deposit_return', methods=['POST'])
@login_required
@apigen.deserialize(schemas.DepositLoadSchema)
def log_deposit_return(data):
    dep = Deposit.query.get(data['id'])
    db.session.delete(dep)
    accounting.log_deposit_return(dep, current_user, data['cash_box'])
    db.session.commit()
    return {}


@app.route('/api/donation', methods=['POST'])
@login_required
@apigen.deserialize(schemas.DonationLoadSchema)
def log_donation(data):
    accounting.log_donation(data['amount'], data['cash_box'])
    db.session.commit()
    return {}


app.route('/api/orders', methods=['GET'])(
login_required(
apigen.endpoint(
        schemas={
            'GET': schemas.OrderDumpSchema,
            'POST': schemas.OrderLoadSchema
        },
        model=Order)
))

app.route('/api/orders', methods=['POST'])(
apigen.endpoint(
        schemas={
            'POST': schemas.OrderLoadSchema
        },
        model=Order)
)

app.route('/api/orders/<int:instance_id>', methods=['GET', 'DELETE'])(
login_required(
apigen.endpoint(
        schemas={'GET': schemas.OrderDumpSchema},
        model=Order,
        allow_delete=True)
))


app.route('/api/lectures')(
apigen.endpoint(
        schemas={'GET': schemas.LectureSchema},
        model=Lecture)
)

# TODO shoehorn this into apigen.endpoint to benefit from automatic jsonquery and pagination
@app.route('/api/lectures/<int:id>/documents')
def lecture_documents(id):
    lecture = Lecture.query.get(id)
    return schemas.serialize(lecture.documents, schemas.DocumentSchema, many=True)


app.route('/api/examinants')(
apigen.endpoint(
        schemas={'GET': schemas.ExaminantSchema},
        model=Examinant)
)

@app.route('/api/examinants/<int:id>/documents')
def examinant_documents(id):
    examinant = Examinant.query.get(id)
    return schemas.serialize(examinant.documents, schemas.DocumentSchema, many=True)

app.route('/api/documents')(
apigen.endpoint(
        schemas={'GET': schemas.DocumentSchema},
        model=Document)
)

app.route('/api/deposits')(
login_required(
apigen.endpoint(
        schemas={'GET': schemas.DepositDumpSchema},
        model=Deposit)
))
