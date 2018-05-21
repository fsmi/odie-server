#! /usr/bin/env python3

from test.harness import OdieTestCase, ODIE_DIR

import config
import datetime
import os
import routes
import json
import random

from flask import session

from db.documents import Document, Lecture
from odie import app, csrf

class APITest(OdieTestCase):
    VALID_USER = 'guybrush'
    VALID_PASS = 'arrrrr'
    CASH_BOX = 'Sprechstundenkasse Informatik'
    UNUSED = 'c9fa0f374b0817113c811bd12d4f1755a572eb37cafdbde05c76803eebec49f1'

    PDF_PATH = os.path.join(ODIE_DIR, 'test/upload.pdf')

    VALID_PRINTJOB = {
            'cover_text': 'Klausuren',
            'document_ids': [1, 2, 2],
            'deposit_count': 1,
            'price': 520,
            'printer': 'FSI-Drucker',
            'cash_box': CASH_BOX,
        }

    VALID_ORDER = {
            'name': UNUSED,
            'document_ids': [2, 1, 5, 4, 3],
        }

    VALID_DEPOSIT_RETURN = {
            'cash_box': CASH_BOX,
            'id': 1,
        }

    VALID_EARLY_DOCUMENT_REWARD = {
            'cash_box': CASH_BOX,
            'id': 6,
        }

    VALID_ACCOUNTING_CORR = {
            'cash_box': CASH_BOX,
            'amount': 42,
        }

    token = None

    def login(self, user=VALID_USER, password=VALID_PASS):
        self.post('/login', data={
                'username': user,
                'password': password
            })
        res = self.get('/api/user_info')
        if res.status_code == 200:
            self.token = self.fromJsonResponse(res)['token']
        return res

    def get(self, *args, **kwargs):
        kwargs.setdefault('headers', {})
        kwargs['headers']['Accept'] = 'text/html;q=0.8, application/json;q=0.9'
        return self.app.get(*args, **kwargs)

    def post(self, *args, **kwargs):
        kwargs.setdefault('headers', {})
        kwargs['headers']['Accept'] = 'text/html;q=0.8, application/json;q=0.9'
        return self.app.post(*args, **kwargs)

    def post_auth(self, *args, **kwargs):
        return self.post(*args, headers={'X-CSRFToken': self.token}, **kwargs)

    def delete_auth(self, *args, **kwargs):
        return self.app.delete(*args, headers={'X-CSRFToken': self.token}, **kwargs)

    def validate_lecture(self, lecture):
        self.assertIn('name', lecture)
        self.assertIn('aliases', lecture)
        self.assertNotIn('name', lecture['aliases'])
        self.assertIn('comment', lecture)

    def validate_document(self, document):
        self.assertIn('department', document)
        self.assertIn('lectures', document)
        # TODO
        pass

    ## tests for unauthenticated api ##

    def test_get_config(self):
        res = self.get('/api/config')
        self.assertEqual(res.status_code, 200)
        data = self.fromJsonResponse(res)
        self.assertIn('DEPOSIT_PRICE', data)
        self.assertIn('OFFICES', data)
        self.assertIn('PRICE_PER_PAGE', data)

    def test_get_lectures(self):
        res = self.get('/api/lectures')
        data = self.fromJsonResponse(res)
        self.assertIsInstance(data, list)
        self.assertTrue(len(data) > 1)

        lecture = random.choice(data)
        self.validate_lecture(lecture)

    def test_get_documents(self):
        res = self.get('/api/documents')
        documents = self.fromJsonResponse(res)
        for doc in documents:
            self.validate_document(doc)
            self.assertNotIn('submitted_by', doc)

    def test_get_documents_logged_in(self):
        self.login()
        res = self.get('/api/documents')
        documents = self.fromJsonResponse(res)
        for doc in documents:
            self.assertIn('submitted_by', doc)

    def test_get_documents_meta(self):
        res = self.get('/api/documents/meta?filters={"includes_lectures":[1]}')
        data = self.fromJsonResponse(res)
        all_docs = Lecture.query.get(1).documents.all()
        self.assertEqual(len(all_docs), data['total_written'] + data['total_oral'])

    def test_get_examinants(self):
        res = self.get('/api/examinants')
        self.fromJsonResponse(res)

    def test_no_kiosk_handover_unauthenticated(self):
        res = self.get('/kiosk')
        self.assertEqual(res.status_code, 401)

    def test_kiosk_handover(self):
        # since we don't have a way to reset the session from outside the request context,
        # we apparently need a new test client for this.
        with app.test_client() as c:
            old_client = self.app
            self.app = c

            self.login()
            res = self.get('/kiosk')
            self.assertEqual(res.status_code, 200)
            self.assertTrue(session['is_kiosk'])

            self.app = old_client

    def test_kiosk_mode_permissions(self):
        with app.test_client() as c:
            old_client = self.app
            self.app = c

            self.login()
            self.get('/kiosk')
            # kiosk mode doesn't mean "logged in"
            res = self.get('/api/user_info')
            self.assertEqual(res.status_code, 401)

            # ...however, viewing PDFs is allowed

            self.assertEqual(self._upload_document().status_code, 200)
            self.login()
            query = json.dumps(self.SUBMITTED_DOC_QUERY, separators=(',', ':'))
            res = self.get('/api/documents?q=%s' % query)
            data = self.fromJsonResponse(res)
            self.assertEqual(len(data), 1)
            id = data[0]['id']
            # we're still in kiosk mode, right?
            self.logout()
            self.assertTrue(session['is_kiosk'])

            # get document
            res = self.get('/api/view/%d' % id)
            self.assertEqual(res.status_code, 200)
            with open(self.PDF_PATH, 'rb') as doc:
                doc_data = doc.read()  # only ~750 bytes...
                self.assertEqual(res.data, doc_data)

            self.app = old_client

    ## login tests ##

    def test_user_info_no_get_unauthenticated(self):
        res = self.get('/api/user_info')
        self.assertEqual(res.status_code, 401)

    def test_login_logout(self):
        def is_logged_in():
            return self.get('/api/user_info').status_code == 200
        self.assertFalse(is_logged_in())
        self.login(self.VALID_USER, self.VALID_PASS)
        self.assertTrue(is_logged_in())
        self.logout()
        self.assertFalse(is_logged_in())

    def test_user_info_get_authenticated(self):
        self.login()
        res = self.get('/api/user_info')
        self.assertEqual(res.status_code, 200)
        data = self.fromJsonResponse(res)
        self.assertIn('user', data)
        self.assertIn('token', data)

    ## tests for authenticated api ##

    def do_print(self, job, auth=False):
        self.app.set_cookie('localhost', 'print_data', json.dumps(job))
        headers = {'Accept': 'text/event-stream'}
        if auth:
            headers['X-CSRFToken'] = self.token
        return self.app.get('/api/print', headers=headers)

    def test_no_printing_unauthenticated(self):
        try:
            csrf._csrf_disable = True  # let's check login_required at least once
            res = self.do_print(self.VALID_PRINTJOB)
            self.assertEqual(res.status_code, 401)
        finally:
            csrf._csrf_disable = False

    # Seasurf doesn't do GET, but EventSource should be pretty XSS safe...
    # def test_no_printing_csrf(self):
    #     self.login()
    #     res = self.do_print(self.VALID_PRINTJOB)
    #     self.assertEqual(res.status_code, 403)

    def test_print(self):
        self.login()
        res = self.do_print(self.VALID_PRINTJOB, auth=True)
        self.assertIn("event: progress\n", res.data.decode('utf8'))
        self.assertNotIn("event: stream-error\n", res.data.decode('utf8'))
        self.assertIn("event: complete\n", res.data.decode('utf8'))
        self.assertEqual(res.status_code, 200)
        self.logout()

    def test_no_print_documents_without_files(self):
        self.login()
        pj = self.VALID_PRINTJOB.copy()
        pj['document_ids'] = [3]  # see fill_data.py to ensure that this document doesn't specify has_file=True
        res = self.do_print(pj, auth=True)
        self.assertIn("event: stream-error\n", res.data.decode('utf8'))
        self.assertEqual(res.status_code, 200)  # connecting to the EventSource should still succeed
        self.logout()

    def test_orders_no_get_unauthenticated(self):
        res = self.get('/api/orders')
        self.assertEqual(res.status_code, 401)

    def test_orders_no_delete_unauthenticated(self):
        res = self.app.delete('/api/orders/1')
        self.assertEqual(res.status_code, 403)

    def test_orders_state(self):
        self.login()
        res = self.get('/api/orders')
        orders = self.fromJsonResponse(res)
        self.assertEqual(res.status_code, 200)
        self.assertIsInstance(orders, list)
        new_order_name = self.VALID_ORDER['name']
        #for order in orders:
         #   self.assertNotEqual(new_order_name, order['name'])

        # ensure POSTing orders is available when not logged in
        self.logout()
        res = self.post('/api/orders', data=json.dumps(self.VALID_ORDER))
        self.fromJsonResponse(res)
        self.assertEqual(res.status_code, 200)
        self.login()

        res = self.get('/api/orders')
        self.assertEqual(res.status_code, 200)
        posted_order = [order for order in self.fromJsonResponse(res) if order['name'] == new_order_name]
        #self.assertEqual(len(posted_order), 1)
        self.assertEqual([doc['id'] for doc in posted_order[0]['documents']],
                         self.VALID_ORDER['document_ids'])
        instance_id = posted_order[0]['id']
        res = self.delete_auth('/api/orders/' + str(instance_id))
        self.assertEqual(res.status_code, 200)
        res = self.get('/api/orders')
        #for order in self.fromJsonResponse(res):
         #   self.assertNotEqual(order['name'], new_order_name)

    def test_deposits_no_get_unauthenticated(self):
        res = self.get('/api/deposits')
        self.assertEqual(res.status_code, 401)

    def test_early_document_reward_no_return_unauthenticated(self):
        res = self.post('/api/log_early_document_reward', data=json.dumps(self.VALID_EARLY_DOCUMENT_REWARD))
        self.assertEqual(res.status_code, 403)

    def test_log_early_document_reward_not_eligible_reward(self):
        self.login()
        res = self.post_auth('/api/log_early_document_reward', data=json.dumps({
            'cash_box': self.CASH_BOX,
            'id': 2,
        }))
        self.assertEqual(res.status_code, 400)

    def test_early_document_reward_disbursal(self):
        self.login()
        res = self.post_auth('/api/log_early_document_reward', data=json.dumps(self.VALID_EARLY_DOCUMENT_REWARD))
        self.assertEqual(res.status_code, 200)
        responseJson = self.fromJsonResponse(res)
        self.assertEqual(responseJson['disbursal'], config.FS_CONFIG['EARLY_DOCUMENT_REWARD'])

    def test_early_document_reward_no_double_disbursal(self):
        self.login()
        res = self.post_auth('/api/log_early_document_reward', data=json.dumps(self.VALID_EARLY_DOCUMENT_REWARD))
        self.assertEqual(res.status_code, 200)
        responseJson = self.fromJsonResponse(res)
        self.assertEqual(responseJson['disbursal'], config.FS_CONFIG['EARLY_DOCUMENT_REWARD'])

        res = self.post_auth('/api/log_early_document_reward', data=json.dumps(self.VALID_EARLY_DOCUMENT_REWARD))
        self.assertEqual(res.status_code, 400)

    def test_early_document_reward_not_eligible(self):
        self.login()
        invalid = self.VALID_EARLY_DOCUMENT_REWARD
        invalid['id'] = 1
        res = self.post_auth('/api/log_early_document_reward', data=json.dumps(invalid))
        self.assertEqual(res.status_code, 400)

    def test_deposits_no_return_unauthenticated(self):
        res = self.post('/api/log_deposit_return', data=json.dumps(self.VALID_DEPOSIT_RETURN))
        self.assertEqual(res.status_code, 403)

    def test_log_deposit_nonexisting_deposit(self):
        self.login()
        res = self.post_auth('/api/log_deposit_return', data=json.dumps({
            'cash_box': self.CASH_BOX,
            'id': 42,
        }))
        self.assertEqual(res.status_code, 400)

    def test_deposits_state(self):
        self.login()
        res = self.get('/api/deposits')
        self.assertEqual(res.status_code, 200)
        deposits = self.fromJsonResponse(res)
        self.assertIsInstance(deposits, list)
        id_to_delete = random.choice(deposits)['id']
        data = self.VALID_DEPOSIT_RETURN
        data['id'] = id_to_delete
        res = self.post_auth('/api/log_deposit_return', data=json.dumps(data))
        self.assertEqual(res.status_code, 200)
        for deposit in self.fromJsonResponse(self.get('/api/deposits')):
            self.assertNotEqual(deposit['id'], id_to_delete)

    def test_log_deposit_return_with_document(self):
        self.assertIsNotNone(Document.query.get(7).submitted_by)
        self.login()
        res = self.post_auth('/api/log_deposit_return', data=json.dumps({
            'cash_box': self.CASH_BOX,
            'id': 1,
            'document_id': 7
        }))
        self.assertEqual(res.status_code, 200)
        self.assertIsNone(Document.query.get(7).submitted_by)

    def test_no_donation_unauthenticated(self):
        res = self.post('/api/donation', data=json.dumps(self.VALID_ACCOUNTING_CORR))
        self.assertEqual(res.status_code, 403)

    def test_donation(self):
        self.login()
        res = self.post_auth('/api/donation', data=json.dumps(self.VALID_ACCOUNTING_CORR))
        self.assertEqual(res.status_code, 200)

    def test_no_log_erroneous_sale_unauthenticated(self):
        res = self.post('/api/log_erroneous_sale', data=json.dumps(self.VALID_ACCOUNTING_CORR))
        self.assertEqual(res.status_code, 403)

    def test_log_erroneous_sale(self):
        self.login()
        res = self.post_auth('/api/log_erroneous_sale', data=json.dumps(self.VALID_ACCOUNTING_CORR))
        self.assertEqual(res.status_code, 200)

    ## pagination tests ##

    # these all depend on the orders endpoint working correctly

    def _add_a_page_of_orders(self):
        for _ in range(config.ITEMS_PER_PAGE):
            res = self.post('/api/orders', data=json.dumps(self.VALID_ORDER))
            self.assertEqual(res.status_code, 200)

    def test_pagination_items_per_page(self):
        self.enable_pagination(3)
        self._add_a_page_of_orders()
        self.login()
        res = self.get('/api/orders')
        data = self.fromJsonResponse(res)
        self.assertEqual(len(data), config.ITEMS_PER_PAGE)

    def test_pagination_out_of_range(self):
        self.enable_pagination(3)
        self.login()
        res = self.get('/api/orders?q={"page":99999}')
        self.assertEqual(res.status_code, 404)

    def test_pagination_number_of_pages(self):
        self.enable_pagination(2)
        self._add_a_page_of_orders()
        self._add_a_page_of_orders()
        self.login()
        ids_seen = []
        for page in range(1, 4):
            res = self.get('/api/orders?q={"page":%d}' % page)
            self.assertEqual(res.status_code, 200)
            data = json.loads(res.data.decode('utf-8'))
            self.assertIn('number_of_pages', data)
            self.assertTrue(data['number_of_pages'] >= 2)
            # assert no ids in this page have been seen before
            self.assertEqual([], [True for item in data['data'] if item['id'] in ids_seen])
            ids_seen += [item['id'] for item in data['data']]

    DOCUMENT_SUBMISSION_JSON = {
                'lectures': [
                    "Fortgeschrittenes Nichtstun",
                ],
                'department': 'computer science',
                'examinants': ["Anon Ymous"],
                'date': '2010-01-01',
                'document_type': 'oral',
                'student_name': UNUSED,
        }

    VALID_DOCUMENT_SUBMISSION = {
                'json': json.dumps(DOCUMENT_SUBMISSION_JSON, separators=(',', ':')),
                'file': None,  # needs to be reopened for every request
            }

    FULL_DOCUMENT_SUBMISSION_JSON = DOCUMENT_SUBMISSION_JSON.copy()
    FULL_DOCUMENT_SUBMISSION_JSON.update({
                'solution': 'official',
                'comment': 'Meh, who cares',
                'document_type': 'written',
            })

    VALID_FULL_DOCUMENT_SUBMISSION = {
                'json': json.dumps(FULL_DOCUMENT_SUBMISSION_JSON, separators=(',', ':')),
                'file': None,  # needs to be reopened for every request
            }

    SUBMITTED_DOC_QUERY = {
                'operator': 'and',
                'value': [{
                    'operator': '==',
                    'column': 'validated',
                    'value': False,
                }, {
                    'operator': '==',
                    'column': 'submitted_by',
                    'value': UNUSED,
                }]
            }

    def _upload_document(self, full=False):
        data = self.VALID_FULL_DOCUMENT_SUBMISSION if full else self.VALID_DOCUMENT_SUBMISSION
        with open(self.PDF_PATH, 'rb') as pdf:
            data['file'] = pdf
            res = self.post('/api/documents', data=data)
            return res

    def test_document_submission(self):
        query = json.dumps(self.SUBMITTED_DOC_QUERY, separators=(',', ':'))
        res = self.get('/api/documents?q=%s' % query)
        self.assertEqual(res.status_code, 200)
        data = self.fromJsonResponse(res)
        self.assertEqual(data, [])
        self.assertEqual(self._upload_document().status_code, 200)

        res = self.get('/api/documents?q=%s' % query)
        self.assertEqual(res.status_code, 200)
        data = self.fromJsonResponse(res)
        self.assertEqual(len(data), 1)

        # We throw away the timezone on the date, so make sure tests and db are
        # executed in the same timezone. (this is due to strptime not supporting
        # the format of timezone info we get)
        frmt = '%Y-%m-%d'
        submitted_date = datetime.datetime.strptime(self.DOCUMENT_SUBMISSION_JSON['date'], frmt).date()
        received_date = datetime.datetime.strptime(data[0]['date'], frmt).date()
        self.assertEqual(submitted_date, received_date)
        # This field will only be populated if the upload succeeded and the PDF was successfully processed
        self.assertEqual(data[0]['number_of_pages'], 1)
        self.assertEqual(len(data[0]['lectures']), len(self.DOCUMENT_SUBMISSION_JSON['lectures']))

    def test_no_full_document_submission_unauthenticated(self):
        res = self._upload_document(full=True).status_code
        self.assertTrue(res != 200 and res != 500)

    def test_full_document_submission(self):
        self.login()
        self.assertEqual(self._upload_document(full=True).status_code, 200)

    def test_no_document_preview_unauthenticated(self):
        self.assertEqual(self._upload_document().status_code, 200)
        res = self.get('/api/view/1')
        self.assertEqual(res.status_code, 401)

    def test_document_preview(self):
        self.assertEqual(self._upload_document().status_code, 200)
        self.login()
        query = json.dumps(self.SUBMITTED_DOC_QUERY, separators=(',', ':'))
        res = self.get('/api/documents?q=%s' % query)
        data = self.fromJsonResponse(res)
        self.assertEqual(len(data), 1)
        id = data[0]['id']

        # get document
        res = self.get('/api/view/%d' % id)
        self.assertEqual(res.status_code, 200)
        with open(self.PDF_PATH, 'rb') as doc:
            doc_data = doc.read()  # only ~750 bytes...
            self.assertEqual(res.data, doc_data)


    ## jsonquery tests ##

    def test_jsonquery_in_op(self):
        res = self.post('/api/orders', data=json.dumps(self.VALID_ORDER))
        self.assertEqual(res.status_code, 200)
        name = json.loads(res.data)
        self.login()
        req = '/api/orders?q={"operator":"in_","column":"name","value":["%s"]}' % name  # self.VALID_ORDER['name']
        res = self.get(req)
        self.assertEqual(res.status_code, 200)
        data = self.fromJsonResponse(res)
        ##self.assertTrue(len(data) == 1)
        self.assertEqual([d['id'] for d in data[0]['documents']], self.VALID_ORDER['document_ids'])

    def test_jsonquery_order(self):
        self.login()
        res = self.get('/api/orders?q={"operator":"order_by_asc","column":"name"}')
        self.assertEqual(res.status_code, 200)
        data = self.fromJsonResponse(res)
        self.assertTrue(len(data) > 2)  # otherwise the ordering is moot anyways...
        last_name = ''
        for item in data:
            self.assertTrue(last_name <= item['name'])
            last_name = item['name']


if __name__ == '__main__':
    unittest.main()
