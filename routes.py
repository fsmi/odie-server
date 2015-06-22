#! /usr/bin/env python3

import accounting
import config
import dateutil.parser
import datetime
import hashlib
import json
import os
import serialization_schemas as schemas

from flask import request
from flask.ext.login import login_user, logout_user, current_user, login_required
from sqlalchemy import and_

from odie import app, db, ClientError
from api_utils import deserialize, endpoint, filtered_results, api_route
from models.documents import Lecture, Deposit, Document, Examinant
from models.odie import Order
from models.public import User

## Routes may either return something which can be turned into json using
## flask.jsonify or a api_utils.PaginatedResult. The actual response is assembled
## in api_utils.api_route.

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
@deserialize(schemas.PrintJobLoadSchema)
@login_required
def print_documents(data):
    ids = data['document_ids']
    document_objs = Document.query.filter(Document.id.in_(ids)).all()
    # sort the docs into the same order they came in the request
    docs_by_id = {doc.id: doc for doc in document_objs}
    documents = [docs_by_id[id] for id in ids]

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
@deserialize(schemas.ErroneousSaleLoadSchema)
def accept_erroneous_sale(data):
    accounting.log_erroneous_sale(data['amount'], current_user, data['cash_box'])
    db.session.commit()
    return {}


@api_route('/api/log_deposit_return', methods=['POST'])
@login_required
@deserialize(schemas.DepositLoadSchema)
def log_deposit_return(data):
    dep = Deposit.query.get(data['id'])
    db.session.delete(dep)
    accounting.log_deposit_return(dep, current_user, data['cash_box'])
    db.session.commit()
    return {}


@api_route('/api/donation', methods=['POST'])
@login_required
@deserialize(schemas.DonationLoadSchema)
def log_donation(data):
    accounting.log_donation(data['amount'], data['cash_box'])
    db.session.commit()
    return {}


api_route('/api/orders', methods=['GET'])(
login_required(
endpoint(
        schemas={
            'GET': schemas.OrderDumpSchema,
            'POST': schemas.OrderLoadSchema
        },
        query=Order.query)
))

api_route('/api/orders', methods=['POST'])(
endpoint(
        schemas={
            'POST': schemas.OrderLoadSchema
        },
        query=Order.query)
)

api_route('/api/orders/<int:instance_id>', methods=['GET', 'DELETE'])(
login_required(
endpoint(
        schemas={'GET': schemas.OrderDumpSchema},
        query=Order.query,
        allow_delete=True)
))


api_route('/api/lectures')(
endpoint(
        schemas={'GET': schemas.LectureDumpSchema},
        query=Lecture.query)
)

@api_route('/api/lectures/<int:id>/documents')
def lecture_documents(id):
    lecture = Lecture.query.get(id)
    return filtered_results(lecture.documents, schemas.DocumentDumpSchema)


api_route('/api/examinants')(
endpoint(
        schemas={'GET': schemas.ExaminantSchema},
        query=Examinant.query)
)

@api_route('/api/examinants/<int:id>/documents')
def examinant_documents(id):
    examinant = Examinant.query.get(id)
    return filtered_results(examinant.documents, schemas.DocumentDumpSchema)


api_route('/api/deposits')(
login_required(
endpoint(
        schemas={'GET': schemas.DepositDumpSchema},
        query=Deposit.query)
))


api_route('/api/documents')(
endpoint(
        schemas={'GET': schemas.DocumentDumpSchema},
        query=Document.query)
)


def _allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in config.SUBMISSION_ALLOWED_FILE_EXTENSIONS


def _document_path(doc):
    assert doc.file_id
    digest = doc.file_id
    return os.path.join(config.DOCUMENT_DIRECTORY, digest[:2], digest + '.pdf')

@api_route('/api/documents', methods=['POST'])
def submit_document():
    """Student document submission endpoint

    POST data must conform to DocumentLoadSchema. For all lectures without
    given id, we first try to find a matching lecture based on its name before
    registering a new lecture.

    Uploaded files are stored in config.DOCUMENT_DIRECTORY. File contents are
    hashed with sha256 and stored in a git-like schema (the first byte of the
    sha256 hex digest are taken as subdirectory name, files are named after this
    digest)."""
    # we can't use @deserialize because this endpoint uses multipart form data
    data = json.loads(request.form['json'])
    (data, errors) = schemas.DocumentLoadSchema().load(data)
    if errors:
        raise ClientError(*errors)
    assert 'file' in request.files
    file = request.files['file']
    if not _allowed_file(file.filename):
        raise ClientError('file extension not allowed', status=406)
    lectures = []
    for lect in data['lectures']:
        l = Lecture.query.filter(and_(Lecture.name == lect['name'], Lecture.subject == lect['subject']))
        if l.count() == 1:
            lectures.append(l.first())
        else:
            # no dice, add a new unverified lecture
            l = Lecture(name=lect['name'],
                    subject=lect['subject'],
                    validated=False)
            lectures.append(l)
            db.session.add(l)
    examinants = []
    for examinant in data['examinants']:
        ex = Examinant.query.filter(Examinant.name == examinant).first()
        if ex:
            examinants.append(ex)
        else:
            ex = Examinant(examinant, validated=False)
            examinants.append(ex)
            db.session.add(ex)
    date = data['date']
    assert date <= datetime.date.today()
    new_doc = Document(
            lectures=lectures,
            examinants=examinants,
            date=date,
            number_of_pages=data['number_of_pages'],
            document_type=data['document_type'],
            validated=False,
            submitted_by=data['student_name'])
    db.session.add(new_doc)

    # we have the db side of things taken care of, now save the file
    # and tell the db where to find the file

    sha256 = hashlib.sha256()
    for bytes in file.stream:
        sha256.update(bytes)
    # reset file stream for saving
    file.stream.seek(0)
    digest = sha256.hexdigest()
    new_doc.file_id = digest
    file.save(_document_path(new_doc))
    db.session.commit()
    return {}
