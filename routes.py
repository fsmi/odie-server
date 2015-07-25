#! /usr/bin/env python3

import barcode
import db.accounting
import config
import datetime
import json
import os
import serialization_schemas as schemas
import socket

from flask import request, send_file, Response
from flask.ext.login import login_user, logout_user, current_user, login_required
from sqlalchemy.orm import subqueryload
from sqlalchemy.orm.exc import NoResultFound

from odie import app, sqla, ClientError
from api_utils import deserialize, endpoint, filtered_results, api_route, handle_client_errors, document_path, save_file
from db.documents import Lecture, Deposit, Document, Examinant
from db.odie import Order
from db.fsmi import User

## Routes may either return something which can be turned into json using
## flask.jsonify or a api_utils.PaginatedResult. The actual response is assembled
## in api_utils.api_route.

@api_route('/api/config')
def get_config():
    return config.FS_CONFIG


## Barcode scanner support is achieved using long-lived HTTP(S) connections and
## server-sent events (https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events)

def scanner_stream(location, id, username):
    assert location in config.FS_CONFIG['OFFICES']
    assert 0 <= id <= len(config.LASER_SCANNERS[location])
    (host, port) = config.LASER_SCANNERS[location][id]
    bs = barcode.BarcodeScanner(host, port, username)
    for doc in bs:
        yield 'data: ' + json.dumps(schemas.serialize(doc, schemas.DocumentDumpSchema)) + '\n\n'
    return


@app.route('/api/scanner/<location>/<int:id>')
@login_required
def scanner(location, id):
    return Response(scanner_stream(location, id, current_user.first_name), mimetype='text/event-stream', headers={'X-Accel-Buffering': 'no'})


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

    if documents:
        paths = [document_path(doc.id) for doc in documents if doc.has_file]
        config.print_documents(paths, data['cover_text'], data['printer'])
        num_pages = sum(doc.number_of_pages for doc in documents)
        db.accounting.log_exam_sale(num_pages, price, current_user, data['cash_box'])
    for _ in range(data['deposit_count']):
        dep = Deposit(
                price=config.FS_CONFIG['DEPOSIT_PRICE'],
                name=data['cover_text'],
                by_user=current_user.full_name,
                lectures=_lectures(data['document_ids']))
        sqla.session.add(dep)
        db.accounting.log_deposit(dep, current_user, data['cash_box'])
    sqla.session.commit()
    return {}


@api_route('/api/log_erroneous_sale', methods=['POST'])
@login_required
@deserialize(schemas.ErroneousSaleLoadSchema)
def accept_erroneous_sale(data):
    db.accounting.log_erroneous_sale(data['amount'], current_user, data['cash_box'])
    sqla.session.commit()
    return {}


@api_route('/api/log_deposit_return', methods=['POST'])
@login_required
@deserialize(schemas.DepositReturnSchema)
def log_deposit_return(data):
    if 'document_id' in data:
        doc = Document.query.get(data['document_id'])
        # data privacy, yo
        doc.submitted_by = None

    dep = Deposit.query.get(data['id'])
    sqla.session.delete(dep)
    db.accounting.log_deposit_return(dep, current_user, data['cash_box'])
    sqla.session.commit()
    return {}


@api_route('/api/donation', methods=['POST'])
@login_required
@deserialize(schemas.DonationLoadSchema)
def log_donation(data):
    db.accounting.log_donation(current_user, data['amount'], data['cash_box'])
    sqla.session.commit()
    return {}


api_route('/api/orders', methods=['GET'])(
login_required(
endpoint(
        schemas={
            'GET': schemas.OrderDumpSchema,
        },
        query=Order.query)
))

api_route('/api/orders', methods=['POST'])(
endpoint(
        schemas={
            'POST': schemas.OrderLoadSchema
        },
        query=None)
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
        query=Lecture.query,
        paginate_many=False)
)

api_route('/api/examinants')(
endpoint(
        schemas={'GET': schemas.ExaminantSchema},
        query=Examinant.query,
        paginate_many=False)
)


def documents_query():
    q = Document.query.options(subqueryload('lectures'), subqueryload('examinants'))
    filters = json.loads(request.args.get('filters', '{}'))
    for id in filters.get('includes_lectures', []):
        q = q.filter(Document.lectures.any(Lecture.id == id))
    for id in filters.get('includes_examinants', []):
        q = q.filter(Document.examinants.any(Examinant.id == id))
    return q

api_route('/api/documents')(
endpoint(
        schemas={'GET': schemas.DocumentDumpSchema},
        query=documents_query)
)

# aggregate values of unpaginated source data
@api_route('/api/documents/meta')
def documents_metadata():
    q = documents_query()
    return {
        'total_written': q.filter_by(document_type='written').count(),
        'total_oral': q.filter(Document.document_type != 'written').count(),
    }


api_route('/api/deposits')(
login_required(
endpoint(
        schemas={'GET': schemas.DepositDumpSchema},
        query=Deposit.query.options(subqueryload('lectures')))
))


def _allowed_file(filename):
    return os.path.splitext(filename)[1] in config.SUBMISSION_ALLOWED_FILE_EXTENSIONS


@api_route('/api/documents', methods=['POST'])
def submit_document():
    """Student document submission endpoint

    POST data must be multipart, with the `json` part conformimg to
    DocumentLoadSchema and the `file` part being a pdf file.

    Uploaded files are stored in config.DOCUMENT_DIRECTORY. File contents are
    hashed with sha256 and stored in a git-like schema (the first byte of the
    sha256 hex digest are taken as subdirectory name, files are named after this
    digest).

    This method may raise AssertionErrors when the user sends invalid data.
    """
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
        try:
            l = Lecture.query.filter_by(name=lect['name'], subject=lect['subject']).one()
            lectures.append(l)
        except NoResultFound:
            # no dice, add a new unverified lecture
            l = Lecture(name=lect['name'],
                    subject=lect['subject'],
                    validated=False)
            lectures.append(l)
            sqla.session.add(l)
    examinants = []
    for examinant in data['examinants']:
        try:
            ex = Examinant.query.filter_by(name=examinant).one()
            examinants.append(ex)
        except NoResultFound:
            ex = Examinant(examinant, validated=False)
            examinants.append(ex)
            sqla.session.add(ex)
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
    sqla.session.add(new_doc)

    # we have the db side of things taken care of, now save the file
    # and tell the db where to find the file
    sqla.session.flush()  # necessary for id field to be populated
    save_file(new_doc, file)
    sqla.session.commit()
    return {}

@app.route('/api/view/<int:instance_id>')
@handle_client_errors
@login_required
def view_document(instance_id):
    doc = Document.query.get(instance_id)
    if doc is None or doc.has_file is None:
        raise ClientError('document not found', status=404)
    return send_file(document_path(doc.id))
