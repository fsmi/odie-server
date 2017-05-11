#! /usr/bin/env python3

import db.accounting
from .common import IdSchema, CashBoxField

from marshmallow import Schema, fields

from odie import sqla
from login import get_user, login_required
from api_utils import deserialize, api_route, ClientError
from db.documents import Deposit, Document, PaymentState

import config

class ErroneousSaleLoadSchema(Schema):
    amount = fields.Int(required=True)
    cash_box = CashBoxField()

# db.accounting does its own logging, so these endpoints don't

@api_route('/api/log_erroneous_sale', methods=['POST'])
@login_required
@deserialize(ErroneousSaleLoadSchema)
def accept_erroneous_sale(data):
    db.accounting.log_erroneous_sale(data['amount'], get_user(), data['cash_box'])
    sqla.session.commit()
    return {}


class DepositReturnSchema(IdSchema):
    cash_box = CashBoxField()
    document_id = fields.Int()

class EarlyDocumentRewardSchema(IdSchema):
    cash_box = CashBoxField()


@api_route('/api/log_deposit_return', methods=['POST'])
@login_required
@deserialize(DepositReturnSchema)
def log_deposit_return(data):
    if 'document_id' in data:
        doc = Document.query.get(data['document_id'])
        if doc is None:
            raise ClientError('document not found')
        doc.deposit_return_state = PaymentState.DISBURSED
        # data privacy, yo
        if doc.early_document_state is not PaymentState.ELIGIBLE:
            doc.submitted_by = None

    dep = Deposit.query.get(data['id'])
    if Deposit.query.filter(Deposit.id == data['id']).delete() == 0:
        raise ClientError('deposit not found')
    db.accounting.log_deposit_return(dep, get_user(), data['cash_box'])
    sqla.session.commit()
    return {}

@api_route('/api/log_early_document_reward', methods=['POST'])
@login_required
@deserialize(EarlyDocumentRewardSchema)
def log_early_document_reward(data):
    doc = Document.query.get(data['id'])
    if doc is None:
        raise ClientError('document not found')
    if doc.early_document_state is not PaymentState.ELIGIBLE:
        raise ClientError('document not eligible for early document reward')

    doc.early_document_state = PaymentState.DISBURSED
    # data privacy, yo
    if doc.deposit_return_state is not PaymentState.ELIGIBLE:
        doc.submitted_by = None

    db.accounting.log_early_document_disburse(get_user(), data['cash_box'])
    sqla.session.commit()

    return {'disbursal': config.FS_CONFIG['EARLY_DOCUMENT_REWARD']}

class DonationLoadSchema(Schema):
    amount = fields.Int(required=True, validate=lambda i: i != 0)
    cash_box = CashBoxField()


@api_route('/api/donation', methods=['POST'])
@login_required
@deserialize(DonationLoadSchema)
def log_donation(data):
    db.accounting.log_donation(get_user(), data['amount'], data['cash_box'])
    sqla.session.commit()
    return {}
