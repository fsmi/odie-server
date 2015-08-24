#! /usr/bin/env python3

import db.accounting
import config

from flask.ext.login import current_user, login_required
from marshmallow import fields, Schema

from .common import CashBoxField, PrinterField
from odie import sqla, ClientError
from api_utils import deserialize, api_route, document_path
from db.documents import Lecture, Deposit, Document


def _lectures(document_ids):
    return Lecture.query.filter(Lecture.documents.any(
        Document.id.in_(document_ids))).all()

def _printable_documents(document_ids):
    document_objs = Document.query.filter(Document.id.in_(document_ids)).all()
    if any(not doc.has_file for doc in document_objs):
        raise ClientError('Tried to print at least one document without file', status=400)
    # sort the docs into the same order they came in the request
    docs_by_id = {doc.id: doc for doc in document_objs}
    return [docs_by_id[id] for id in document_ids]


class PrintForFolderLoadSchema(Schema):
    cover_text = fields.Str(required=True)
    document_ids = fields.List(fields.Int(), required=True)
    printer = PrinterField()


@api_route('/api/print_for_folder', methods=['POST'])
@deserialize(PrintForFolderLoadSchema)
@login_required
def print_for_folder(data):
    documents = _printable_documents(data['document_ids'])
    paths = [document_path(doc.id) for doc in documents]
    usercode = config.PRINTER_USERCODES['internal']
    config.print_documents(paths, data['cover_text'], data['printer'], usercode)
    for doc in documents:
        doc.present_in_physical_folder = True
    sqla.session.commit()


class PrintJobLoadSchema(Schema):
    cover_text = fields.Str(required=True)
    cash_box = CashBoxField()
    document_ids = fields.List(fields.Int(), required=True)
    deposit_count = fields.Int(required=True)
    printer = PrinterField()


@api_route('/api/print', methods=['POST'])
@deserialize(PrintJobLoadSchema)
@login_required
def print_documents(data):
    documents = _printable_documents(data['document_ids'])

    assert data['deposit_count'] >= 0
    price = sum(doc.price for doc in documents)
    # round up to next 10 cents
    price = 10 * (price/10 + (1 if price % 10 else 0))

    if documents:
        paths = [document_path(doc.id) for doc in documents]
        usercode = config.PRINTER_USERCODES[data['cash_box']]
        config.print_documents(paths, data['cover_text'], data['printer'], usercode)
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
