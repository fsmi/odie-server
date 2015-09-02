#! /usr/bin/env python3

import db.accounting
import config

from flask.ext.login import current_user, login_required
from marshmallow import fields, Schema

from .common import CashBoxField, PrinterField
from odie import sqla, ClientError
from api_utils import deserialize, api_route, document_path
from db.documents import Lecture, Deposit, Document


class PrintJobLoadSchema(Schema):
    cover_text = fields.Str(required=True)
    cash_box = CashBoxField()
    document_ids = fields.List(fields.Int(), required=True)
    deposit_count = fields.Int(required=True)
    printer = PrinterField()
    price = fields.Int(required=True)  # for validation


# all interesting actions in this route are logged by the db accounting side

@api_route('/api/print', methods=['POST'])
@deserialize(PrintJobLoadSchema)
@login_required
def print_documents(data):
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

    if documents:
        try:
            config.print_documents(
                doc_paths=[document_path(doc.id) for doc in documents],
                cover_text=data['cover_text'],
                printer=data['printer'],
                usercode=config.PRINTER_USERCODES[data['cash_box']],
                job_title="Odie-Druck für {}".format(data['cover_text'].split(' ')[0]))
        except Exception as e:
            # This isn't really a ClientError, but this is the only endpoint we have that has proper error states,
            # so it's not worth it to differentiate. The error code is an arbitrary unreserved 5xx code.
            raise ClientError('Printing failed: ' + '\n'.join(e.args), status=507)
        num_pages = sum(doc.number_of_pages for doc in documents)
        db.accounting.log_exam_sale(num_pages, print_price, current_user, data['cash_box'])
    for _ in range(data['deposit_count']):
        lectures = Lecture.query.filter(Lecture.documents.any(Document.id.in_(document_ids))).all()
        dep = Deposit(
                price=config.FS_CONFIG['DEPOSIT_PRICE'],
                name=data['cover_text'],
                by_user=current_user.full_name,
                lectures=lectures)
        sqla.session.add(dep)
        db.accounting.log_deposit(dep, current_user, data['cash_box'])
    sqla.session.commit()
    return {}
