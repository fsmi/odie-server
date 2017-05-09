#! /usr/bin/env python3

"""
This file handles inserting accouting information into garfield

If garfield is ever replaced, replace the functions nopped out
at the beginning of this file.

Sorry about the literal SQL statements, but reflecting the tables
incurred a >1s lag on startup.

Unless stated otherwise, parameters are supposed to be of the type as
specified in their respective marshmallow schemas (e.g. printjob should have
the fields of a deserialized PrintJobSchema). Monetary parameters
(price/amount) are to be entered in cents and converted to whatever
the database internally uses in the logging functions
"""

from sqlalchemy import cast, text, String
from odie import app, sqla

import config
import sqlalchemy

class AccountingException(Exception):
    pass

# pylint: disable=function-redefined
def log_donation(user, amount: int, cashbox: str):
    app.logger.info("Donation: {} put {} cents into {}".format(user.username, amount, cashbox))
def log_exam_sale(pages: int, price: int, user, cashbox: str):
    app.logger.info("Exam Sale: {} sold {} pages, put {} cents into {}".format(user.username, pages, price, cashbox))
def log_erroneous_sale(price: int, user, cashbox: str):
    app.logger.info("Correction: {} marked {} cents from {} as erroneously sold".format(user.username, price, cashbox))
def log_deposit(deposit, user, cashbox: str):
    app.logger.info("Deposit: {} put {} cents into {}".format(user.username, deposit.price, cashbox))
def log_deposit_return(deposit, user, cashbox: str):
    app.logger.info("Deposit: {} returned deposit to {}, took {} cents out of {}".format(user.username, deposit.name, deposit.price, cashbox))
def log_early_document_disburse(costumer: str, user, cashbox: str):
    app.logger.info("Early Document: {} payed early document reward to {}, took {} cents out of {}".format(user.username, costumer, config.FS_CONFIG['EARLY_DOCUMENT_REWARD'], cashbox))

if not config.LOCAL_SERVER:

    procs = sqlalchemy.sql.func.garfield
    _qry = text("""SELECT cash_box_name, cash_boxes.cash_box_id
            FROM garfield.cash_boxes;""")
    cash_box_ids = dict(sqla.session.execute(_qry).fetchall())
    # tax group for exam sales
    _tax_group = 2


    def _garfield_user_id(user):
        qry = text("""SELECT user_id FROM garfield.users WHERE user_name = :username""")
        r = sqla.session.execute(qry.bindparams(username=user.username)).scalar()
        if r is None:
            raise AccountingException('User not found: %s' % user.username)
        return r


    def log_donation(user, amount: int, cashbox: str):
        user_id = _garfield_user_id(user)
        amount = amount / 100  # garfield uses floats, because of course it does
        proc = procs.donation_accept(cash_box_ids[cashbox], 'MONEY', amount, user_id)
        app.logger.info("Donation: {} put {} € into {}".format(user.username, amount, cashbox))
        sqla.session.execute(proc).scalar()


    def _log_exam_action(pages: int, final_price: float, user, cashbox: str, action: str):
        # Without these casts, the strings will end up as type 'unknown' in postgres, where the function lookup will fail due to incorrect type signature
        action_string = cast(action, String)
        username = cast(user.username, String)
        proc = procs.exam_sale_action(cash_box_ids[cashbox], action_string, final_price, username, pages, _tax_group, config.FS_CONFIG['PRICE_PER_PAGE'] / 100)
        sqla.session.execute(proc)


    def log_exam_sale(pages: int, price: int, user, cashbox: str):
        price = price / 100
        app.logger.info("Exam Sale: {} sold {} pages, put {} € into {}".format(user.username, pages, price, cashbox))
        _log_exam_action(pages, price, user, cashbox, 'EXAM_SALE')


    def log_erroneous_sale(price: int, user, cashbox: str):
        """price is assumed to be positive"""
        price = price / -100
        app.logger.info("Correction: {} marked {} € from {} as erroneously sold".format(user.username, price, cashbox))
        _log_exam_action(0, price, user, cashbox, 'EXAM_SALE_CANCEL')


    def _log_deposit_action(deposit, user, cashbox: str, final_amount: float, action: str):
        # Without these casts, the strings will end up as type 'unknown' in postgres, where the function lookup will fail due to incorrect type signature
        username = cast(user.username, String)
        action_string = cast(action, String)
        deposit_name = cast(deposit.name, String)
        proc = procs.exam_deposit_action(cash_box_ids[cashbox], action_string, final_amount, username, deposit_name)
        sqla.session.execute(proc)


    def log_deposit(deposit, user, cashbox: str):
        price = deposit.price / 100
        app.logger.info("Deposit: {} put {} € into {}".format(user.username, price, cashbox))
        _log_deposit_action(deposit, user, cashbox, price, 'EXAM_DEPOSIT_PAYMENT')

    def log_deposit_return(deposit, user, cashbox: str):
        price = deposit.price / -100
        app.logger.info("Deposit: {} returned deposit to {}, took {} € out of {}".format(user.username, deposit.name, price, cashbox))
        _log_deposit_action(deposit, user, cashbox, price, 'EXAM_DEPOSIT_WITHDRAWAL')


    def _log_early_document_disburse(costumer: str, user, cashbox: str, final_amount: float):
        # Without these casts, the strings will end up as type 'unknown' in postgres, where the function lookup will fail due to incorrect type signature
        username = cast(user.username, String)
        costumer_string= cast(costumer, String)
        proc = procs.exam_deposit_action(cash_box_ids[cashbox], final_amount, username, costumer_string)
        sqla.session.execute(proc)

    def log_early_document_disburse(costumer: str, user, cashbox: str):
       price = config.FS_CONFIG['EARLY_DOCUMENT_REWARD'] / -100
       app.logger.info("Early Document: {} payed early document reward to {}, took {} € out of {}".format(user.username, costumer, price, cashbox))
       _log_early_document_disburse(costumer, user, cashbox, price)
