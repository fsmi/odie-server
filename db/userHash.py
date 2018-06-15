#! /usr/bin/env python3

import config
from odie import sqla, Column
from db.documents import Deposit, Document
from db.odie import Order

import random
from marshmallow import Schema, fields
from sqlalchemy.dialects import postgresql
from sqlalchemy import func
from sqlalchemy.orm import column_property
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.sql import not_, select
from db import garfield
from pytz import reference

from db import garfield

# this class is to handle Exceptions
class ToManyAttempts(Exception):
    def __init__(self, message, errors):
        super.__init__(message)

        self.errors = errors

# this class you can use to generate an collision free unique hash of an specific transcation
class userHash:

    # this function set the length of the string
    # it retuns an id in the coressponding length
    def setLength(self, integer):
        defined_length = 8
        ret = ""

        for i in range(0, defined_length):
            if integer < pow(10,i):
                ret += '0'

        ret += str(integer)
        return ret

    # this function create and returns the sales id
    def returnIdSales(self):
        for i in range(0, 6):
            if i == 5:
                raise ToManyAttempts('to many attempts')

            min = 0
            max = 99999999
            rand = 's' + self.setLength(random.randint(min, max))

            db = Deposit.query.filter_by(name = rand).first()
            if db is None:
                break


        return rand

    # this function create and returns the card id
    def returnIdCard(self):
        for i in range(0, 6):
            if i == 5:
                raise ToManyAttempts('to many attempts')

            min = 0
            max = 99999999
            rand = 'c' + self.setLength(random.randint(min, max))

            db = Order.query.filter_by(name = rand).first()
            if db is None:
                break


        return rand

    # this function create and returns the upload id
    def returnIdUpload(self):
        for i in range(0, 6):
            if i == 5:
                raise ToManyAttempts('to many attempts')

            min = 0
            max = 99999999
            rand = 'u' + self.setLength(random.randint(min, max))

            db = Document.query.filter_by(submitted_by = rand).first()
            print(db)
            if db is None:
                break

        return rand