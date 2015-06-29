#! /usr/bin/env python3

"""
This file handles inserting accouting information into garfield

If garfield is ever replaced, replace the functions nopped out
at the beginning of this file.

Sorry about the literal SQL statements, but reflecting the tables
incurred a >1s lag on startup.

Unless stated otherwise, parameters are supposed to be of the type as
specified in serialization_schemas.py (e.g. printjob should have
the fields of a deserialized PrintJobSchema). Monetary parameters
(price/amount) are to be entered in cents and converted to whatever
the database internally uses in the logging functions
"""

import sqlalchemy
from sqlalchemy import text
from sqlalchemy.orm import Session
from odie import db
import config
import datetime


def log_donation(user, amount: int, cashbox: str):
    pass
def log_exam_sale(pages: int, price: int, user, cashbox: str):
    pass
def log_erroneous_sale(price: int, user, cashbox: str):
    pass
def log_deposit(deposit, user, cashbox: str):
    pass
def log_deposit_return(deposit, user, cashbox: str):
    pass

if config.GARFIELD_ACCOUNTING:

    _qry = text("""SELECT cash_box_name, cash_boxes.cash_box_id
            FROM garfield.cash_boxes;""")
    cash_box_ids = dict(db.session.execute(_qry).fetchall())
    # tax group for exam sales
    _tax_group = 2


    def _cash_box_log_entry(user, cashbox: str, amount: float, action: str):
        qry = text("""INSERT INTO garfield.cash_box_log
                (cash_box_log_performed_by_user_id, cash_box_id, cash_box_log_quantity, type_id, receipt_number)
                SELECT user_id, :cash_box_id, :amount, :type, garfield.cash_box_log_get_receipt_number(:cash_box_id, current_date)
                FROM garfield.users
                WHERE user_name = :user_name
                RETURNING cash_box_log_id;""")
        r = db.session.execute(qry.bindparams(
                user_name=user.username,
                cash_box_id=cash_box_ids[cashbox],
                amount=amount,
                type=action,
            ))
        return r.scalar()

    def log_donation(user, amount: int, cashbox: str):
        # I'd love to use donation_accept, but that thing wants to be smart and
        # guesses the user id from the session user, which doesn't exist.
        # So... more raw SQL it is.
        log_id = _cash_box_log_entry(user, cashbox, amount / 100, 'DONATION')
        qry = text("""INSERT INTO garfield.donation_sales_log
                VALUES (:log_id, 'MONEY');""")
        db.session.execute(qry.bindparams(log_id=log_id))

    def _log_exam_action(pages: int, final_price: float, user, cashbox: str, action: str):
        cshbx_log_id = _cash_box_log_entry(user, cashbox, price, action)
        qry = text("""INSERT INTO garfield.exam_sale_log
                (cash_box_log_id, tax_id, price_per_page, pages)
                VALUES (:cshbx_log_id, garfield.tax_find(:tax_group, current_date), :ppp, :pages);""")
        db.session.execute(qry.bindparams(
                cshbx_log_id=cshbx_log_id,
                tax_group=_tax_group,
                ppp=config.FS_CONFIG['PRICE_PER_PAGE'] / 100,
                pages=pages
            ))

    def log_exam_sale(pages: int, price: int, user, cashbox: str):
        _log_exam_action(pages, price / 100, user, cashbox, 'EXAM_SALE')

    def log_erroneous_sale(price: int, user, cashbox: str):
        """price is assumed to be positive"""
        _log_exam_action(0, price / -100, user, cashbox, 'EXAM_SALE_CANCEL')


    def _log_deposit_action(deposit, user, cashbox: str, amount: int, action :str):
        cshbx_log_id = _cash_box_log_entry(user, cashbox, amount, action)
        qry = text("""INSERT INTO garfield.exam_deposit_log
                (student_name, cash_box_log_id)
                VALUES (:student_name, :log_id);""")
        db.session.execute(qry.bindparams(
                student_name=deposit.name,
                log_id=cshbx_log_id
            ))

    def log_deposit(deposit, user, cashbox: str):
        _log_deposit_action(deposit, user, cashbox,
                config.FS_CONFIG['DEPOSIT_PRICE'] / 100,
                'EXAM_DEPOSIT_PAYMENT')

    def log_deposit_return(deposit, user, cashbox: str):
        _log_deposit_action(deposit, user, cashbox,
                config.FS_CONFIG['DEPOSIT_PRICE'] / -100,
                'EXAM_DEPOSIT_WITHDRAWAL')
