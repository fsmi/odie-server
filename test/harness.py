#! /usr/bin/env python3

import config
import json
import os
import subprocess
import unittest
import odie

ODIE_DIR = os.path.join(os.path.dirname(__file__), os.pardir)

class OdieTestCase(unittest.TestCase):

    def fromJsonResponse(self, response):
        return json.loads(response.data.decode('utf-8'))['data']

    def logout(self):
        return self.app.post('/api/logout')

    def setUp(self):
        # this should go without saying, but... don't run these tests in production
        assert config.FlaskConfig.DEBUG, "These tests are destructive, I refuse to run them in production"
        subprocess.call([os.path.join(ODIE_DIR, 'delete_everything_in_all_databases.sh')], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.call([os.path.join(ODIE_DIR, 'fill_data.py')], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.app = odie.app.test_client()

    def tearDown(self):
        # just in case a test failed after logging in
        self.logout()

