#! /usr/bin/env python3

import app

from app import db
from sqlalchemy.dialects import postgres


class Lecture(db.Model):
    __tablename__ = 'lectures'
    __table_args__ = app.documents_table_args

    id = app.Column(db.Integer, primary_key=True)
    name = app.Column(db.String(256))
    aliases = app.Column(postgres.ARRAY(db.String(256)))
    subject = app.Column(postgres.ENUM('mathematics', 'computer science', 'both', name='subject'))
    comment = app.Column(db.String(256), nullable=True)


lectureDocs = db.Table('lecture_docs',
        app.Column('lecture_id', db.Integer, db.ForeignKey('documents.lectures.id')),
        app.Column('document_id', db.Integer, db.ForeignKey('documents.documents.id')),
        **app.documents_table_args)

documentExaminants = db.Table('document_examinants',
        app.Column('document_id', db.Integer, db.ForeignKey('documents.documents.id')),
        app.Column('examinant_id', db.Integer, db.ForeignKey('documents.examinants.id')),
        **app.documents_table_args)


class Document(db.Model):
    __tablename__ = 'documents'
    __table_args__ = app.documents_table_args

    id = app.Column(db.Integer, primary_key=True)
    legacy_id = app.Column(db.Integer, default=0)
    lectures = db.relationship('Lecture', secondary=lectureDocs,
            backref=db.backref('documents'))
    examinants = db.relationship('Examinant', secondary=documentExaminants,
            backref=db.backref('documents'))
    date = app.Column(postgres.DATE)
    number_of_pages = app.Column(db.Integer)
    solution = app.Column(postgres.ENUM('official', 'inofficial', 'none', name='solution'), default='none')
    comment = app.Column(db.String(80), nullable=True)
    documentType = app.Column(postgres.ENUM('oral', 'written', 'oral reexam', name='type'))
    file_id = app.Column(db.String(256), nullable=True)  # usually sha256sum of file


class Examinant(db.Model):
    __tablename__ = 'examinants'
    __table_args__ = app.documents_table_args

    id = app.Column(db.Integer, primary_key=True)
    name = app.Column(db.String(80))


depositLectures = db.Table('deposit_lectures',
        app.Column('deposit_id', db.Integer, db.ForeignKey('documents.deposits.id')),
        app.Column('lecture_id', db.Integer, db.ForeignKey('documents.lectures.id')),
        **app.documents_table_args)


class Deposit(db.Model):
    __tablename__ = 'deposits'
    __table_args__ = app.documents_table_args

    id = app.Column(db.Integer, primary_key=True)
    price = app.Column(db.Integer)
    name = app.Column(db.String(80))
    lectures = db.relationship('Lecture', secondary=depositLectures)


