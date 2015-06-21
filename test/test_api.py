#! /usr/bin/env python3

import odie
import config
import routes
import json
import random

from test.harness import OdieTestCase

class APITest(OdieTestCase):
    VALID_USER = 'guybrush'
    VALID_PASS = 'arrrrr'
    CASH_BOX = 'Sprechstundenkasse Informatik'

    VALID_PRINTJOB = {
            'cover_text': 'Klausuren',
            'document_ids': [1,2,2],
            'deposit_count': 1,
            'printer': 'external',
            'cash_box': CASH_BOX,
        }

    VALID_ORDER = {
            'name': "a747b53e0d942681791b",
            'document_ids': [1],
        }

    VALID_DEPOSIT_RETURN = {
            'cash_box': CASH_BOX,
            'id': 1,
        }

    VALID_ACCOUNTING_CORR = {
            'cash_box': CASH_BOX,
            'amount': 42,
        }

    def login(self, user=VALID_USER, password=VALID_PASS):
        return self.app.post('/api/login', data=json.dumps({
                'username': user,
                'password': password
            }))

    def validate_lecture(self, lecture):
        self.assertIn('name', lecture)
        self.assertIn('aliases', lecture)
        self.assertNotIn('name', lecture['aliases'])
        self.assertIn('subject', lecture)
        self.assertIsInstance(lecture['subject'], str)
        self.assertIn('comment', lecture)

    def validate_document(self, document):
        self.assertIn('lectures', document)
        # TODO
        pass

    ## tests for unauthenticated api ##

    def test_get_config(self):
        res = self.app.get('/api/config')
        self.assertEqual(res.status_code, 200)
        data = self.fromJsonResponse(res)
        self.assertIn('DEPOSIT_PRICE', data)
        self.assertIn('PRINTERS', data)
        self.assertIn('CASH_BOXES', data)
        self.assertIn('PRICE_PER_PAGE', data)

    def test_get_lectures(self):
        res = self.app.get('/api/lectures')
        data = self.fromJsonResponse(res)
        self.assertIsInstance(data, list)
        self.assertTrue(len(data) > 1)

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
        res = self.app.post('/api/login', data=json.dumps({'username':self.VALID_USER}))
        self.assertEqual(res.status_code, 400)

    def test_invalid_login(self):
        res = self.login(user='I am not a username', password='neither am I a password')
        self.assertEqual(res.status_code, 401)

    def test_valid_login(self):
        res = self.login(self.VALID_USER, self.VALID_PASS)
        self.assertEqual(res.status_code, 200)

    def test_login_no_get_unauthenticated(self):
        res = self.app.get('/api/login')
        self.assertEqual(res.status_code, 401)

    def test_login_logout(self):
        def is_logged_in():
            return self.app.post('/api/login', data=json.dumps({})).status_code == 200
        self.assertFalse(is_logged_in())
        self.login(self.VALID_USER, self.VALID_PASS)
        self.assertTrue(is_logged_in())
        self.logout()
        self.assertFalse(is_logged_in())

    def test_login_get_authenticated(self):
        self.login()
        res = self.app.get('/api/login')
        self.assertEqual(res.status_code, 200)
        data = self.fromJsonResponse(res)
        self.assertIn('username', data)
        self.assertIn('first_name', data)
        self.assertIn('last_name', data)

    ## tests for authenticated api ##

    def test_no_printing_unauthenticated(self):
        res = self.app.post('/api/print', data=json.dumps(self.VALID_PRINTJOB))
        self.assertEqual(res.status_code, 401)

    def test_print(self):
        self.login()
        res = self.app.post('api/print', data=json.dumps(self.VALID_PRINTJOB))
        self.fromJsonResponse(res)
        self.assertEqual(res.status_code, 200)
        self.logout()

    def test_orders_no_get_unauthenticated(self):
        res = self.app.get('/api/orders')
        self.assertEqual(res.status_code, 401)

    def test_orders_no_delete_unauthenticated(self):
        res = self.app.delete('/api/orders/1')
        self.assertEqual(res.status_code, 401)

    def test_orders_state(self):
        self.login()
        res = self.app.get('/api/orders')
        orders = self.fromJsonResponse(res)
        self.assertEqual(res.status_code, 200)
        self.assertIsInstance(orders, list)
        new_order_name = self.VALID_ORDER['name']
        for order in orders:
            self.assertNotEqual(new_order_name, order['name'])

        # ensure POSTing orders is available when not logged in
        self.logout()
        res = self.app.post('/api/orders', data=json.dumps(self.VALID_ORDER))
        self.fromJsonResponse(res)
        self.assertEqual(res.status_code, 200)
        self.login()

        res = self.app.get('/api/orders')
        self.assertEqual(res.status_code, 200)
        posted_order = [order for order in self.fromJsonResponse(res) if order['name'] == new_order_name]
        self.assertEqual(len(posted_order), 1)
        self.assertEqual(posted_order[0]['documents'][0]['id'], 1)
        instance_id = posted_order[0]['id']
        res = self.app.delete('/api/orders/' + str(instance_id))
        self.assertEqual(res.status_code, 200)
        res = self.app.get('/api/orders')
        for order in self.fromJsonResponse(res):
            self.assertNotEqual(order['name'], new_order_name)

    def test_deposits_no_get_unauthenticated(self):
        res = self.app.get('/api/deposits')
        self.assertEqual(res.status_code, 401)

    def test_deposits_no_return_unauthenticated(self):
        res = self.app.post('/api/log_deposit_return', data=json.dumps(self.VALID_DEPOSIT_RETURN))
        self.assertEqual(res.status_code, 401)

    def test_deposits_state(self):
        self.login()
        res = self.app.get('/api/deposits')
        self.assertEqual(res.status_code, 200)
        deposits = self.fromJsonResponse(res)
        self.assertIsInstance(deposits, list)
        id_to_delete = random.choice(deposits)['id']
        data = self.VALID_DEPOSIT_RETURN
        data['id'] = id_to_delete
        res = self.app.post('/api/log_deposit_return', data=json.dumps(data))
        self.assertEqual(res.status_code, 200)
        for deposit in self.fromJsonResponse(self.app.get('/api/deposits')):
            self.assertNotEqual(deposit['id'], id_to_delete)

    def test_no_donation_unauthenticated(self):
        res = self.app.post('/api/donation', data=json.dumps(self.VALID_ACCOUNTING_CORR))
        self.assertEqual(res.status_code, 401)

    def test_donation(self):
        self.login()
        res = self.app.post('/api/donation', data=json.dumps(self.VALID_ACCOUNTING_CORR))
        self.assertEqual(res.status_code, 200)

    def test_no_log_erroneous_sale_unauthenticated(self):
        res = self.app.post('/api/log_erroneous_sale', data=json.dumps(self.VALID_ACCOUNTING_CORR))
        self.assertEqual(res.status_code, 401)

    def test_log_erroneous_sale(self):
        self.login()
        res = self.app.post('/api/log_erroneous_sale', data=json.dumps(self.VALID_ACCOUNTING_CORR))
        self.assertEqual(res.status_code, 200)

    ## pagination tests ##

    # these all depend on the orders endpoint working correctly

    def _add_a_page_of_orders(self):
        for _ in range(config.ITEMS_PER_PAGE):
            res = self.app.post('/api/orders', data=json.dumps(self.VALID_ORDER))
            self.assertEqual(res.status_code, 200)

    def test_pagination_items_per_page(self):
        self.enable_pagination(3)
        self._add_a_page_of_orders()
        self.login()
        res = self.app.get('/api/orders')
        data = self.fromJsonResponse(res)
        self.assertEqual(len(data), config.ITEMS_PER_PAGE)

    def test_pagination_out_of_range(self):
        self.enable_pagination(3)
        self.login()
        res = self.app.get('/api/orders?page=99999')
        self.assertEqual(res.status_code, 404)

    def test_pagination_number_of_pages(self):
        self.enable_pagination(2)
        self._add_a_page_of_orders()
        self._add_a_page_of_orders()
        self.login()
        ids_seen = []
        for page in range(1, 4):
            res = self.app.get('/api/orders?page=%d' % page)
            self.assertEqual(res.status_code, 200)
            data = json.loads(res.data.decode('utf-8'))
            self.assertIn('number_of_pages', data)
            self.assertTrue(data['number_of_pages'] >= 2)
            # assert no ids in this page have been seen before
            self.assertEqual([], [True for item in data['data'] if item['id'] in ids_seen])
            ids_seen += [item['id'] for item in data['data']]

    ## jsonquery tests ##

    def test_jsonquery_in_op(self):
        res = self.app.post('/api/orders', data=json.dumps(self.VALID_ORDER))
        self.assertEqual(res.status_code, 200)
        self.login()
        req = '/api/orders?q={"operator":"in_","column":"name","value":["%s"]}' % self.VALID_ORDER['name']
        res = self.app.get(req)
        self.assertEqual(res.status_code, 200)
        data = self.fromJsonResponse(res)
        self.assertTrue(len(data) == 1)
        self.assertEqual([d['id'] for d in data[0]['documents']], self.VALID_ORDER['document_ids'])

    def test_jsonquery_order(self):
        self.login()
        res = self.app.get('/api/orders?q={"operator":"order_by_asc","column":"name"}')
        self.assertEqual(res.status_code, 200)
        data = self.fromJsonResponse(res)
        self.assertTrue(len(data) > 2)  # otherwise the ordering is moot anyways...
        last_name = ''
        for item in data:
            self.assertTrue(last_name <= item['name'])
            last_name = item['name']


if __name__ == '__main__':
    unittest.main()
