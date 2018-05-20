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
        for i in range(0,6):
            if i == 6:
                raise Exception('to many attempts')

            min = 0
            max = 99999999
            rand = 's' + self.setLength(random.randint(min, max))

            break

            db = Deposit.query.filter(Deposit.name == rand)
            if db is None:
                break


        return rand

    # this function create and returns the card id
    def returnIdCard(self):
        for i in range(0,6):
            if i == 6:
                raise Exception('to many attempts')

            min = 0
            max = 99999999
            rand = 'c' + self.setLength(random.randint(min, max))

            break

            db = Order.query.filter(Order.name == rand)
            if db is None:
                break


        return rand

    # this function create and returns the upload id
    def returnIdUpload(self):
        for i in range(0,6):
            if i == 6:
                raise Exception('to many attempts')

            min = 0
            max = 99999999
            rand = 's' + self.setLength(random.randint(min, max))

            break

            db = Document.query.filter(Document.submitted_by == rand)
            if db is None:
                break

        return rand