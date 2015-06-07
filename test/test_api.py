#! /usr/bin/env python3

import odie
import routes
import json
import random

from test.harness import OdieTestCase

class APITest(OdieTestCase):
    VALID_USER = 'guybrush'
    VALID_PASS = 'arrrrr'

    VALID_PRINTJOB = {
            'coverText': 'Klausuren',
            'document_ids': [1,2,2],
            'depositCount': 1,
            'printer': 'external'
        }

    def login(self, user=VALID_USER, password=VALID_PASS):
        return self.app.post('/api/login', data=json.dumps({
                'username': user,
                'password': password
            }))

    def validate_lecture(self, lecture):
        assert 'name' in lecture
        assert 'aliases' in lecture
        assert 'name' not in lecture['aliases']
        assert 'subject' in lecture and isinstance(lecture['subject'], str)
        assert 'comment' in lecture

    def validate_document(self, document):
        assert 'lectures' in document
        # TODO
        pass

    ## tests for unauthenticated api ##

    def test_get_config(self):
        res = self.app.get('/api/config')
        assert res.status_code == 200
        data = self.fromJsonResponse(res)
        assert 'DEPOSIT_PRICE' in data
        assert 'PRINTERS' in data
        assert 'CASH_BOXES' in data
        assert 'PRICE_PER_PAGE' in data

    def test_get_lectures(self):
        res = self.app.get('/api/lectures')
        data = self.fromJsonResponse(res)
        assert isinstance(data, list) and len(data) > 1

        lecture = random.choice(data)
        self.validate_lecture(lecture)

    def test_get_lecture_documents(self):
        res = self.app.get('/api/lectures/1/documents')
        documents = self.fromJsonResponse(res)
        for doc in documents:
            self.validate_document(doc)

    def test_get_documents(self):
        res = self.app.get('/api/documents')
        data = self.fromJsonResponse(res)

    def test_get_examinants(self):
        res = self.app.get('/api/examinants')
        data = self.fromJsonResponse(res)


    ## login tests ##

    def test_malformed_login(self):
        res = self.app.post('/api/login', data=json.dumps({'user':self.VALID_USER}))
        assert res.status_code == 400

    def test_invalid_login(self):
        res = self.login(user='I am not a username', password='neither am I a password')
        assert res.status_code == 401

    def test_valid_login(self):
        res = self.login(self.VALID_USER, self.VALID_PASS)
        assert res.status_code == 200

    def test_login_no_get(self):
        res = self.app.get('/api/login')
        assert res.status_code == 405

    def test_login_logout(self):
        def is_logged_in():
            return self.app.post('/api/login', data=json.dumps({})).status_code == 200
        assert not is_logged_in()
        self.login(self.VALID_USER, self.VALID_PASS)
        assert is_logged_in()
        self.logout()
        assert not is_logged_in()

    ## tests for authenticated api ##

    def test_no_printing_unauthenticated(self):
        res = self.app.post('/api/print', data=json.dumps(self.VALID_PRINTJOB))
        assert res.status_code == 401

    def test_print(self):
        self.login()
        res = self.app.post('api/print', data=json.dumps(self.VALID_PRINTJOB))
        self.fromJsonResponse(res)
        assert res.status_code == 200
        self.logout()

    def test_orders_no_get_unauthenticated(self):
        res = self.app.get('/api/orders')
        assert res.status_code == 401

    def test_orders_no_delete_unauthenticated(self):
        res = self.app.delete('/api/orders/1')
        assert res.status_code == 401

    def test_orders_state(self):
        self.login()
        res = self.app.get('/api/orders')
        orders = self.fromJsonResponse(res)
        assert res.status_code == 200
        assert isinstance(orders, list)
        new_order_name = "a747b53e0d942681791b"
        for order in orders:
            assert new_order_name != order['name']
        new_order = {
                'name': new_order_name,
                'document_ids': [1],
            }

        # ensure POSTing orders is available when not logged in
        self.logout()
        res = self.app.post('/api/orders', data=json.dumps(new_order))
        self.fromJsonResponse(res)
        assert res.status_code == 200
        self.login()

        res = self.app.get('/api/orders')
        assert res.status_code == 200
        posted_order = [order for order in self.fromJsonResponse(res) if order['name'] == new_order_name]
        assert len(posted_order) == 1
        assert posted_order[0]['documents'][0]['id'] == 1
        instance_id = posted_order[0]['id']
        res = self.app.delete('/api/orders/' + str(instance_id))
        assert res.status_code == 200
        res = self.app.get('/api/orders')
        for order in self.fromJsonResponse(res):
            assert order['name'] != new_order_name

    def test_deposits_no_get_unauthenticated(self):
        res = self.app.get('/api/deposits')
        assert res.status_code == 401

    def test_deposits_no_delete_unauthenticated(self):
        res = self.app.delete('/api/deposits/1')
        assert res.status_code == 401

    def test_deposits_state(self):
        self.login()
        res = self.app.get('/api/deposits')
        assert res.status_code == 200
        deposits = self.fromJsonResponse(res)
        assert isinstance(deposits, list)
        id_to_delete = random.choice(deposits)['id']
        res = self.app.delete('/api/deposits/' + str(id_to_delete))
        assert res.status_code == 200
        for deposit in self.fromJsonResponse(self.app.get('/api/deposits')):
            assert deposit['id'] != id_to_delete


if __name__ == '__main__':
    unittest.main()
