#! /usr/bin/env python3

import db.accounting
import config
import urllib.parse

from flask import request
from flask.ext.login import current_user, login_required
from marshmallow import fields, Schema

from .common import CashBoxField, PrinterField
from odie import app, sqla, ClientError
from api_utils import document_path, event_stream, handle_client_errors, NonConfidentialException
from db.documents import Lecture, Deposit, Document


class PrintJobLoadSchema(Schema):
    cover_text = fields.Str(required=True)
    cash_box = CashBoxField()
    document_ids = fields.List(fields.Int(), required=True)
    deposit_count = fields.Int(required=True)
    printer = PrinterField()
    price = fields.Int(required=True)  # for validation


# all interesting actions in this route are logged by the db accounting side

@app.route('/api/print') # can't use POST for an EventSource
@handle_client_errors
@login_required
@event_stream
def print_documents():
    # GET params could be too limited. therefore, cookies.
    (data, errors) = PrintJobLoadSchema().loads(urllib.parse.unquote(request.cookies['print_data']))
    if errors:
        raise ClientError(*errors)
    document_ids = data['document_ids']
    document_objs = Document.query.filter(Document.id.in_(document_ids)).all()
    if any(not doc.has_file for doc in document_objs):
        raise ClientError('Tried to print at least one document without file', status=400)
    # sort the docs into the same order they came in the request
    docs_by_id = {doc.id: doc for doc in document_objs}
    documents = [docs_by_id[id] for id in document_ids]

    assert data['deposit_count'] >= 0
    print_price = sum(doc.price for doc in documents)
    # round up to next 10 cents
    print_price = 10 * (print_price//10 + (1 if print_price % 10 else 0))
    assert print_price + data['deposit_count'] * config.FS_CONFIG['DEPOSIT_PRICE'] == data['price']

    # pull current_user out of app context
    user = current_user._get_current_object()
    yield None  # exit application context, start event stream

    if documents:
        try:
            for _ in config.print_documents(
                    doc_paths=[document_path(doc.id) for doc in documents],
                    cover_text=data['cover_text'],
                    printer=data['printer'],
                    usercode=config.PRINTER_USERCODES[data['cash_box']],
                    job_title="Odie-Druck für {}".format(data['cover_text'].split(' ')[0])):
                yield ('progress', '')
        except Exception as e:
            raise NonConfidentialException('Printing failed: ' + str(e)) from e
    try:
        if documents:
            num_pages = sum(doc.number_of_pages for doc in documents)
            db.accounting.log_exam_sale(num_pages, print_price, user, data['cash_box'])
        for _ in range(data['deposit_count']):
            lectures = Lecture.query.filter(Lecture.documents.any(Document.id.in_(document_ids))).all()
            dep = Deposit(
                    price=config.FS_CONFIG['DEPOSIT_PRICE'],
                    name=data['cover_text'],
                    by_user=user.full_name,
                    lectures=lectures)
            sqla.session.add(dep)
            db.accounting.log_deposit(dep, user, data['cash_box'])
        sqla.session.commit()
    except Exception as e:
        # in case of network troubles, we've just printed a set of documents but screwed up accounting.
        raise NonConfidentialException('Printing succeeded, but account logging failed. Exception: ' + str(e)) from e
    yield ('complete', '')
