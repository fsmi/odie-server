#! /usr/bin/env python3

import config

from flask.ext.login import current_user
from functools import partial
from marshmallow import fields, Schema
from marshmallow.utils import missing
from marshmallow.validate import OneOf


class IdSchema(Schema):
    id = fields.Int(required=True)


class DocumentDumpSchema(IdSchema):
    department = fields.Str()
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
        return obj.submitted_by if current_user.is_authenticated else missing


CashBoxField = partial(fields.Str, required=True, validate=OneOf([cash_box for office in config.FS_CONFIG['OFFICES'].values() for cash_box in office['cash_boxes']]))
PrinterField = partial(fields.Str, required=True, validate=OneOf([printer for office in config.FS_CONFIG['OFFICES'].values() for printer in office['printers']]))
