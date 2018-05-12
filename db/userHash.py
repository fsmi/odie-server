#! /usr/bin/env python3

import config
from odie import sqla, Column
from db.documents import Deposit

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

    # this function returns the last used id
    # @param table is the table which should be used
    def returnIdSales(self):
        for i in range(0,6):
            if i == 6:
                raise Exception('to many attempts')

            min = 0
            max = 99999999
            rand = 's' + str(random.randint(min, max))

            db = Deposit.query.filter(Deposit.name == rand)
            if db is None:
                break


        return rand

