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
            'documents': [1,2,2],
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
        assert 'subject' in lecture and type(lecture['subject']) is str
        assert 'comment' in lecture

    def validate_document(self, document):
        assert 'lectures' in document
        # TODO
        pass

    def test_get_lectures(self):
        res = self.app.get('/api/lectures')
        data = self.fromJsonResponse(res)
        assert type(data) is list and len(data) > 1

        lecture = random.choice(data)
        self.validate_lecture(lecture)

        res = self.app.get('/api/lectures/' + str(random.randint(1,len(data))))
        lecture = self.fromJsonResponse(res)
        self.validate_lecture(lecture)
        assert 'documents' in lecture and type(lecture['documents']) is list
        self.validate_document(random.choice(lecture['documents']))

    def test_get_documents(self):
        res = self.app.get('/api/documents')
        data = self.fromJsonResponse(res)

    def test_get_examinants(self):
        res = self.app.get('/api/examinants')
        data = self.fromJsonResponse(res)

    def test_malformed_login(self):
        res = self.app.post('/api/login', data=json.dumps({'user':self.VALID_USER}))
        assert res.status_code != 200

    def test_invalid_login(self):
        res = self.login(user='I am not a username', password='neither am I a password')
        assert res.status_code != 200

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

    def test_no_printing_unauthenticated(self):
        res = self.app.post('/api/print', data=json.dumps(self.VALID_PRINTJOB))
        assert res.status_code != 200

    def test_print(self):
        self.login()
        res = self.app.post('api/print', data=json.dumps(self.VALID_PRINTJOB))
        assert res.status_code == 200
        self.logout()



if __name__ == '__main__':
    unittest.main()
