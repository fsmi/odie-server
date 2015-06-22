#! /usr/bin/env python3

"""Fills the sample database with some sample data"""


import odie
import models
import crypt

from odie import db

from models.documents import Lecture, Document, Examinant, Deposit
from models.public import User
from models.acl import Permission
from models.odie import Order

from datetime import datetime as time

# force creation of schemas and tables
import create_schemas_and_tables

def fill():
    lectures = [
            Lecture(name='Fortgeschrittenes Nichtstun', aliases=['Ugh'], subject='both', validated=True),
            Lecture(name='Moderne Programmierumgebungen am Beispiel von .SEXY', aliases=['.SEXY'], subject='computer science', validated=True),
            Lecture(name='"Advanced" Operating Systems', aliases=['Stupid Operating Systems'], subject='computer science', validated=True),
            Lecture(name='Einführung in die Kozuch-Theorie', aliases=[], subject='mathematics', validated=True),
            Lecture(name='Einführung in Redundanz', aliases=['Redundanz'], subject='computer science', validated=True),
            Lecture(name='Nanokernel Construction', aliases=[], subject='computer science', validated=True),
            Lecture(name='Mensch-Toastbrot-Toaster-Kommunikation', aliases=['MTTK'], subject='computer science', validated=True),
            Lecture(name='Einf�hrung in Encoding', aliases=['=?ISO-8859-1?Q?Einf?hrung in Encoding'], subject='computer science', validated=True),
        ]

    for l in lectures:
        db.session.add(l)

    profs = [
                Examinant(name='Bemens Clöhm', validated=True),
                Examinant(name='Prof. Doktór Üñícøðé', validated=True),
                Examinant(name='Martina Zartbitter', validated=True),
                Examinant(name='Anon Ymous', validated=True),
            ]

    for p in profs:
        db.session.add(p)

    db.session.add(Deposit(by_user="guybrush", price=5, name='Sloth', lectures=[lectures[0]]))
    db.session.add(Deposit(by_user="guybrush", price=10, name='Montgomery Montgomery', lectures=[lectures[4],lectures[5],lectures[6],lectures[7]]))
    db.session.add(Deposit(by_user="guybrush", price=5, name='Random J. Hacker', lectures=[lectures[1], lectures[2], lectures[7]]))

    docs = [
                Document(lectures=[lectures[0], lectures[1], lectures[5]], examinants=[profs[3]], date=time(2010, 4, 1), number_of_pages=4, document_type='oral', file_id='577c8472f37734e6960c2062a43435ff4823e69a1dbacfe6675e00333ed077f3', validated=True),
                Document(lectures=[lectures[6], lectures[7]], examinants=[profs[1]], date=time(2004, 10, 4), number_of_pages=1, document_type='oral', file_id='577c8472f37734e6960c2062a43435ff4823e69a1dbacfe6675e00333ed077f3', validated=True),
                Document(lectures=[lectures[4], lectures[3], lectures[2]], examinants=[profs[1], profs[0]], date=time(2004, 8, 2), number_of_pages=2, document_type='oral', validated=True),
                Document(lectures=[lectures[5], lectures[6], lectures[7]], examinants=[profs[3], profs[0], profs[2]], date=time(2000, 1, 1), number_of_pages=7, document_type='oral', validated=True),
                Document(lectures=[lectures[5], lectures[6], lectures[7]], examinants=[profs[3], profs[0], profs[2]], date=time(2000, 2, 3), number_of_pages=7, document_type='oral', validated=True),
        ]

    for d in docs:
        db.session.add(d)





    # Order

    db.session.add(Order(name='Hatsune Miku', document_ids=[1,4], creation_time=time(2009, 4, 2)))
    db.session.add(Order(name='Megurine Luka', document_ids=[4,3,2], creation_time=time(2012, 10, 10)))
    db.session.add(Order(name='Kagamine Rin', document_ids=[2], creation_time=time(2011, 1, 3)))
    db.session.add(Order(name='Kagamine Len', document_ids=[2], creation_time=time(2014, 1, 2)))




    # Users and auth

    def hash(pw):
        return crypt.crypt(pw, pw)  # what the flying fuck.

    perms = [
                Permission(name='homepage_login'),
                Permission(name='homepage_logout'),
                Permission(name='partying')
            ]

    for p in perms:
        db.session.add(p)

    users = [
                User(username='guybrush', first_name='Guybrush', last_name='Threepwood', pw_hash=hash('arrrrr'), effective_permissions=[perms[2], perms[0]]),
                User(username='lechuck', first_name='Ghost Pirate', last_name='leChuck', pw_hash=hash('grrrrr'), effective_permissions=[])
            ]

    for u in users:
        db.session.add(u)

    db.session.commit()

if __name__ == '__main__':
    fill()
