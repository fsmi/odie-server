#! /usr/bin/env python3

import config
from odie import sqla, Column

import sqlalchemy
from sqlalchemy import func
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import query
from sqlalchemy.sql import select

from db import garfield

# this class you can use to generate an collision free unique hash of an specific transcation
class userHash:

    # this function returns the last used id
    def returnLastUsedId(self):
        multprimary = 104729
        difprimary = 5
        # set table and table args of the last transaction

        id = sqla.text("""SELECT max(id) FROM orders""")
        res = (id * multprimary) / difprimary
        return res

