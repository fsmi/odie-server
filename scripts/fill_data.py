#! /usr/bin/env python3
# -*- coding: UTF-8 -*-
"""Fills the sample database with some sample data"""

try:
    import hack
except:
    from scripts import hack

import db
import crypt

from odie import sqla

from db.documents import Lecture, Document, Examinant, Deposit, Folder, PaymentState
from db.garfield import Location
from db.fsmi import User
from db.acl import Permission
from db.odie import Order

from datetime import date, datetime

# force creation of schemas and tables
import create_schemas_and_tables

def fill():
    lectures = [
            Lecture(name='Fortgeschrittenes Nichtstun', aliases=['Ugh'], validated=True),
            Lecture(name='Moderne Programmierumgebungen am Beispiel von .SEXY', aliases=['.SEXY'], validated=True),
            Lecture(name='"Advanced" Operating Systems', aliases=['Stupid Operating Systems'], validated=True),
            Lecture(name='Einführung in die Kozuch-Theorie', aliases=[], validated=True),
            Lecture(name='Einführung in Redundanz', aliases=['Redundanz'], validated=True),
            Lecture(name='Nanokernel Construction', aliases=[], validated=True),
            Lecture(name='Mensch-Toastbrot-Toaster-Kommunikation', aliases=['MTTK'], validated=True),
            Lecture(name='Einf�hrung in Encoding', aliases=['=?ISO-8859-1?Q?Einf?hrung in Encoding'], validated=True),
        ]

    for l in lectures:
        sqla.session.add(l)

    profs = [
                Examinant(name='Bemens Clöhm', validated=True),
                Examinant(name='Prof. Doktór Üñícøðé', validated=True),
                Examinant(name='Martina Zartbitter', validated=True),
                Examinant(name='Anon Ymous', validated=True),
            ]

    for p in profs:
        sqla.session.add(p)

    sqla.session.add(Deposit(by_user="guybrush", price=500, name='Sloth', lectures=[lectures[0]]))
    sqla.session.add(Deposit(by_user="guybrush", price=1000, name='Montgomery Montgomery', lectures=[lectures[4],lectures[5],lectures[6],lectures[7]]))
    sqla.session.add(Deposit(by_user="guybrush", price=500, name='Random J. Hacker', lectures=[lectures[1], lectures[2], lectures[7]]))

    # assumptions in tests: the first two documents have has_file=True, the third one doesn't
    docs = [
                Document(department='computer science', lectures=[lectures[0], lectures[1], lectures[5]], examinants=[profs[3]], date=date(2010, 4, 1), validation_time=datetime(2010, 4, 2), number_of_pages=4, document_type='oral', validated=True, has_file=True, early_document_state=PaymentState.NOT_ELIGIBLE, deposit_return_state=PaymentState.NOT_ELIGIBLE),
                Document(department='computer science', lectures=[lectures[6], lectures[7]], examinants=[profs[1]], date=date(2004, 10, 4), number_of_pages=1, validation_time=datetime(2010, 10, 5), document_type='oral', validated=True, has_file=True, early_document_state=PaymentState.NOT_ELIGIBLE, deposit_return_state=PaymentState.NOT_ELIGIBLE),
                Document(department='computer science', lectures=[lectures[4], lectures[3], lectures[2]], examinants=[profs[1], profs[0]], date=date(2004, 8, 2), validation_time=datetime(2010, 8, 3), number_of_pages=2, document_type='oral', validated=True, early_document_state=PaymentState.NOT_ELIGIBLE, deposit_return_state=PaymentState.NOT_ELIGIBLE),
                Document(department='mathematics', lectures=[lectures[5], lectures[6], lectures[7]], examinants=[profs[3], profs[0], profs[2]], date=date(2000, 1, 1), validation_time=datetime(2000, 1, 2), number_of_pages=7, document_type='oral', validated=True, early_document_state=PaymentState.NOT_ELIGIBLE, deposit_return_state=PaymentState.NOT_ELIGIBLE),
                Document(department='mathematics', lectures=[lectures[5], lectures[6], lectures[7]], examinants=[profs[3], profs[0], profs[2]], date=date(2000, 2, 3), validation_time=datetime(2000, 2, 4), number_of_pages=7, document_type='oral', validated=True, early_document_state=PaymentState.NOT_ELIGIBLE, deposit_return_state=PaymentState.NOT_ELIGIBLE),
                Document(department='mathematics', lectures=[lectures[5], lectures[6], lectures[7]], examinants=[profs[3], profs[0], profs[2]], date=date(2001, 2, 3), validation_time=datetime(2001, 2, 4), number_of_pages=2, document_type='oral', validated=False, submitted_by='Monty Montgomery', early_document_state=PaymentState.ELIGIBLE, deposit_return_state=PaymentState.ELIGIBLE),
                Document(department='mathematics', lectures=[lectures[5], lectures[6], lectures[7]], examinants=[profs[3], profs[0], profs[2]], date=date(2001, 2, 3), validation_time=datetime(2001, 2, 4), number_of_pages=2, document_type='oral', validated=False, submitted_by='Some other Monty', early_document_state=PaymentState.NOT_ELIGIBLE, deposit_return_state=PaymentState.ELIGIBLE),
        ]

    for d in docs:
        sqla.session.add(d)


    # Location

    fsi = Location(name='FSI', description='Info-Raum')
    sqla.session.add(fsi)
    fsm = Location(name='FSM', description='Mathe-Raum')
    sqla.session.add(fsm)


    # Folder

    folders = [
        Folder(name='Mündliche Nachprüfungen', document_type='oral reexam', location=fsi),  # hyper-special folder
        Folder(name='Fo realz', examinants=[profs[0], profs[2]], document_type='oral', location=fsi),
        Folder(name='Best buddies', lectures=[lectures[7]], examinants=[profs[2]], document_type='written', location=fsm),
    ]

    for f in folders:
        sqla.session.add(f)


    # Order

    sqla.session.add(Order(name='Hatsune Miku', document_ids=[1,4], creation_time=datetime(2009, 4, 2)))
    sqla.session.add(Order(name='Megurine Luka', document_ids=[4,3,2], creation_time=datetime(2012, 10, 10)))
    sqla.session.add(Order(name='Kagamine Rin', document_ids=[2], creation_time=datetime(2011, 1, 3)))
    sqla.session.add(Order(name='Kagamine Len', document_ids=[2], creation_time=datetime(2014, 1, 2)))


    # Users and auth

    def hash(pw):
        return crypt.crypt(pw, pw)  # what the flying fuck.

    perms = [
                Permission(name='homepage_login'),
                Permission(name='homepage_logout'),
                Permission(name='partying'),
                Permission(name='info_klausuren'),
                Permission(name='info_protokolle'),
                Permission(name='fsusers'),
                Permission(name='adm'),
            ]

    for p in perms:
        sqla.session.add(p)

    users = [
                User(username='guybrush', first_name='Guybrush', last_name='Threepwood', pw_hash=hash('arrrrr'), effective_permissions=[perms[2], perms[0]]),
                User(username='elaine', first_name='Elaine', last_name='Marley', pw_hash=hash('arrrrr'), effective_permissions=[perms[0], perms[4], perms[5]]),
                User(username='lechuck', first_name='Ghost Pirate', last_name='leChuck', pw_hash=hash('grrrrr'), effective_permissions=[]),
                User(username='admin', first_name='Ad', last_name='Min', pw_hash=hash('admin'), effective_permissions=perms)
            ]

    for u in users:
        sqla.session.add(u)

    sqla.session.commit()

if __name__ == '__main__':
    fill()
