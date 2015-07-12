#! /usr/bin/env python3

try:
    import hack
except:
    from scripts import hack

#pylint: disable=unused-import
import odie
import admin
import routes

from odie import app

if __name__ == '__main__':
    app.run()
