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

# To make the server available externally, change the app.run line to app.run(threaded=True,host='0.0.0.0')
if __name__ == '__main__':
    app.run(threaded=True)
