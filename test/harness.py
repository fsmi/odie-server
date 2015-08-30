#! /usr/bin/env python3

import config
import json
import os
import subprocess
import unittest

from odie import app, sqla
from scripts import fill_data

ODIE_DIR = os.path.join(os.path.dirname(__file__), os.pardir)

class OdieTestCase(unittest.TestCase):

    def fromJsonResponse(self, response):
        data = json.loads(response.data.decode('utf-8'))
        assert 'errors' not in data, data['errors']
        return data['data']

    def logout(self):
        return self.get('/logout')

    @classmethod
    def setUpClass(cls):
        # this should go without saying, but... don't run these tests in production
        assert config.FlaskConfig.DEBUG and config.LOCAL_SERVER, "These tests are destructive, I refuse to run them in production"
        subprocess.call([os.path.join(ODIE_DIR, 'scripts', 'delete_everything_in_all_databases.sh')], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.call([os.path.join(ODIE_DIR, 'scripts', 'create_schemas_and_tables.py')], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        cls.app = app.test_client()

    @staticmethod
    def clear_all():
        # http://stackoverflow.com/a/5003705/161659
        for table in reversed(sqla.metadata.sorted_tables):
            sqla.session.execute(table.delete())

        # http://www.postgresql.org/message-id/20060509072129.93529.qmail@web30409.mail.mud.yahoo.com
        for sequence in sqla.session.execute(
                """
                SELECT n.nspname, relname
                FROM pg_class
                JOIN pg_namespace n ON relnamespace = n.oid
                WHERE relkind='S'
                """):
            sqla.session.execute("ALTER SEQUENCE {}.{} RESTART WITH 1".format(*sequence))
        sqla.session.commit()

    def disable_pagination(self):
        self.original_items_per_page = config.ITEMS_PER_PAGE
        # eh, close enough
        config.ITEMS_PER_PAGE = 9999

    def enable_pagination(self, items_per_page=None):
        config.ITEMS_PER_PAGE = items_per_page or self.original_items_per_page

    def setUp(self):
        # reset DB
        self.clear_all()
        fill_data.fill()
        self.disable_pagination()


    def tearDown(self):
        # just in case a test failed after logging in
        self.logout()
