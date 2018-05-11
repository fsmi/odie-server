#! /usr/bin/env python3

import config
from odie import sqla

# this class you can use to generate an collision free unique hash of an specific transcation
class userHash:

    # this function returns the last used id
    def returnLastUsedId(self):