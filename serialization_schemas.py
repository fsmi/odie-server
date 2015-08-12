#! /usr/bin/env python3

from flask.ext.login import current_user
from functools import partial
from marshmallow import Schema, fields
from marshmallow.utils import missing
from marshmallow.validate import OneOf

import config
from db.odie import Order
from odie import ClientError

CashBoxField = partial(fields.Str, required=True, validate=OneOf([cash_box for office in config.FS_CONFIG['OFFICES'].values() for cash_box in office['cash_boxes']]))
PrinterField = partial(fields.Str, required=True, validate=OneOf([printer for office in config.FS_CONFIG['OFFICES'].values() for printer in office['printers']]))

def serialize(data, schema, many=False):
    res = schema().dump(data, many)
    if res.errors:
        raise ClientError(*res.errors)
    else:
        return res.data


class IdSchema(Schema):
    id = fields.Int(required=True)


class PaginatedResultSchema(Schema):
    data = fields.Raw()
    page = fields.Int(attribute='pagination.page')
    number_of_pages = fields.Int(attribute='pagination.pages')
    total = fields.Int(attribute='pagination.total')


class UserLoadSchema(Schema):
    username = fields.Str(required=True)
    password = fields.Str(required=True)


class UserDumpSchema(Schema):
    username = fields.Str()
    first_name = fields.Str()
    last_name = fields.Str()
    office = fields.Function(config.try_get_office)


class DocumentDumpSchema(IdSchema):
    lectures = fields.List(fields.Nested(IdSchema))
    examinants = fields.List(fields.Nested(IdSchema))
    date = fields.Date()
    number_of_pages = fields.Int()
    solution = fields.Str()
    comment = fields.Str()
    document_type = fields.Str()
    available = fields.Boolean(attribute='has_file')
    validated = fields.Boolean()
    validation_time = fields.Date()
    submitted_by = fields.Method('scrub_submitted_by')

    @staticmethod
    def scrub_submitted_by(obj):
        return obj.submitted_by if current_user.is_authenticated() else missing

class ExaminantSchema(IdSchema):
    name = fields.Str()
    validated = fields.Boolean()


class OrderLoadSchema(Schema):
    name = fields.Str(required=True)
    document_ids = fields.List(fields.Int(), required=True)

    def make_object(self, data):
        try:
            return Order(name=data['name'],
                         document_ids=data['document_ids'])
        except KeyError:
            return None


class OrderDumpSchema(IdSchema):
    name = fields.Str()
    documents = fields.List(fields.Nested(DocumentDumpSchema))
    creation_time = fields.Date()


class LectureDumpSchema(IdSchema):
    name = fields.Str()
    aliases = fields.List(fields.Str())
    subject = fields.Str()
    comment = fields.Str()
    validated = fields.Boolean()


class DocumentLoadSchema(Schema):  # used by student document submission
    lectures = fields.List(fields.Str(), required=True)
    examinants = fields.List(fields.Str(), required=True)
    date = fields.Date(required=True)
    document_type = fields.Str(required=True, validate=OneOf(['oral', 'oral reexam']))
    student_name = fields.Str(required=True)
    subject = fields.Str(required=True, validate=OneOf(['computer science', 'mathematics', 'both', 'other']))


class DepositDumpSchema(IdSchema):
    price = fields.Int()
    name = fields.Str()
    date = fields.Date()
    lectures = fields.List(fields.Str())


class DepositReturnSchema(IdSchema):
    cash_box = CashBoxField()
    document_id = fields.Int()


class PrintJobLoadSchema(Schema):
    cover_text = fields.Str(required=True)
    cash_box = CashBoxField()
    document_ids = fields.List(fields.Int(), required=True)
    deposit_count = fields.Int(required=True)
    printer = PrinterField()


class DonationLoadSchema(Schema):
    amount = fields.Int(required=True, validate=lambda i: i != 0)
    cash_box = CashBoxField()


class ErroneousSaleLoadSchema(Schema):
    amount = fields.Int(required=True, validate=lambda i: i > 0)
    cash_box = CashBoxField()

