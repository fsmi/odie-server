#! /usr/bin/env python3

from datetime import datetime as time
from functools import partial
from marshmallow import Schema, fields

import config
from models.documents import Document
from models.odie import Order
from odie import ClientError

CashBoxField = partial(fields.Str, required=True, validate=lambda s: s in config.FS_CONFIG['CASH_BOXES'])
PrinterField = partial(fields.Str, required=True, validate=lambda s: s in config.FS_CONFIG['PRINTERS'])

def serialize(data, schema, many=False):
    res = schema().dump(data, many)
    if res.errors:
        raise ClientError(*res.errors)
    else:
        return res.data


class IdSchema(Schema):
    id = fields.Int(required=True)


class UserLoadSchema(Schema):
    username = fields.Str(required=True)
    password = fields.Str(required=True)


class UserDumpSchema(Schema):
    username = fields.Str()
    first_name = fields.Str()
    last_name = fields.Str()


class DocumentSchema(IdSchema):
    lectures = fields.List(fields.Nested(IdSchema))
    examinants = fields.List(fields.Nested(IdSchema))
    date = fields.Date()
    number_of_pages = fields.Int()
    solution = fields.Str()
    comment = fields.Str()
    document_type = fields.Str()
    available = fields.Method('is_available_for_printing')

    def is_available_for_printing(self, obj):
        return obj.file_id is not None


class ExaminantSchema(IdSchema):
    name = fields.Str()


class OrderLoadSchema(Schema):
    name = fields.Str(required=True)
    document_ids = fields.List(fields.Int(), required=True)

    def make_object(self, data):
        try:
            return Order(name=data['name'],
                         document_ids=data['document_ids'])
        except KeyError:
            raise ClientError('invalid json. name or document_ids missing?')


class OrderDumpSchema(IdSchema):
    name = fields.Str()
    documents = fields.List(fields.Nested(DocumentSchema))


class LectureSchema(IdSchema):
    name = fields.Str()
    aliases = fields.List(fields.Str())
    subject = fields.Str()
    comment = fields.Str()


class DepositDumpSchema(IdSchema):
    price = fields.Int()
    name = fields.Str()
    lectures = fields.List(fields.Str())


class DepositLoadSchema(IdSchema):
    cash_box = CashBoxField()


class PrintJobLoadSchema(Schema):
    coverText = fields.Str(required=True)
    document_ids = fields.List(fields.Int(), required=True)
    deposit_count = fields.Int(required=True)
    printer = PrinterField()


class DonationLoadSchema(Schema):
    amount = fields.Int(required=True, validate=lambda i: i > 0)
    cash_box = CashBoxField()


class ErroneousSaleLoadSchema(Schema):
    amount = fields.Int(required=True, validate=lambda i: i > 0)
    cash_box = CashBoxField()

