#! /usr/bin/env python3

import db.accounting
from .common import IdSchema, CashBoxField

from flask.ext.login import current_user, login_required
from marshmallow import Schema, fields

from odie import sqla
from api_utils import deserialize, api_route
from db.documents import Deposit, Document


class ErroneousSaleLoadSchema(Schema):
    amount = fields.Int(required=True, validate=lambda i: i > 0)
    cash_box = CashBoxField()


@api_route('/api/log_erroneous_sale', methods=['POST'])
@login_required
@deserialize(ErroneousSaleLoadSchema)
def accept_erroneous_sale(data):
    db.accounting.log_erroneous_sale(data['amount'], current_user, data['cash_box'])
    sqla.session.commit()
    return {}


class DepositReturnSchema(IdSchema):
    cash_box = CashBoxField()
    document_id = fields.Int()


@api_route('/api/log_deposit_return', methods=['POST'])
@login_required
@deserialize(DepositReturnSchema)
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


class DonationLoadSchema(Schema):
    amount = fields.Int(required=True, validate=lambda i: i != 0)
    cash_box = CashBoxField()


@api_route('/api/donation', methods=['POST'])
@login_required
@deserialize(DonationLoadSchema)
def log_donation(data):
    db.accounting.log_donation(current_user, data['amount'], data['cash_box'])
    sqla.session.commit()
    return {}
