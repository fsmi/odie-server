#! /usr/bin/env python3

import odie
import config

from odie import db, Column
from sqlalchemy.dialects import postgres


class Lecture(db.Model):
    __tablename__ = 'lectures'
    __table_args__ = config.documents_table_args

    id = Column(db.Integer, primary_key=True)
    name = Column(db.String)
    aliases = Column(postgres.ARRAY(db.String), server_default='{}')
    subject = Column(db.Enum('mathematics', 'computer science', 'both', name='subject', inherit_schema=True))
    comment = Column(db.String, server_default='')

    def __str__(self):
        return self.name


lectureDocs = db.Table('lecture_docs',
        Column('lecture_id', db.Integer, db.ForeignKey('documents.lectures.id')),
        Column('document_id', db.Integer, db.ForeignKey('documents.documents.id')),
        **config.documents_table_args)

documentExaminants = db.Table('document_examinants',
        Column('document_id', db.Integer, db.ForeignKey('documents.documents.id')),
        Column('examinant_id', db.Integer, db.ForeignKey('documents.examinants.id')),
        **config.documents_table_args)


class Document(db.Model):
    __tablename__ = 'documents'
    __table_args__ = config.documents_table_args

    id = Column(db.Integer, primary_key=True)
    lectures = db.relationship('Lecture', secondary=lectureDocs,
            backref=db.backref('documents'))
    examinants = db.relationship('Examinant', secondary=documentExaminants,
            backref=db.backref('documents'))
    date = Column(db.DateTime)
    number_of_pages = Column(db.Integer)
    solution = Column(db.Enum('official', 'inofficial', 'none', name='solution', inherit_schema=True), nullable=True)
    comment = Column(db.String, server_default='')
    document_type = Column(db.Enum('oral', 'written', 'oral reexam', name='type', inherit_schema=True))
    file_id = Column(db.String, nullable=True)  # usually sha256sum of file

    @property
    def examinants_names(self):
        return [ex.name for ex in self.examinants]

    @property
    def examinants_ids(self):
        return [ex.id for ex in self.examinants]

    @property
    def price(self):
        return config.FS_CONFIG['PRICE_PER_PAGE'] * self.number_of_pages



class Examinant(db.Model):
    __tablename__ = 'examinants'
    __table_args__ = config.documents_table_args

    id = Column(db.Integer, primary_key=True)
    name = Column(db.String)

    def __str__(self):
        return self.name


depositLectures = db.Table('deposit_lectures',
        Column('deposit_id', db.Integer, db.ForeignKey('documents.deposits.id')),
        Column('lecture_id', db.Integer, db.ForeignKey('documents.lectures.id')),
        **config.documents_table_args)


class Deposit(db.Model):
    __tablename__ = 'deposits'
    __table_args__ = config.documents_table_args

    id = Column(db.Integer, primary_key=True)
    price = Column(db.Integer)
    name = Column(db.String)
    by_user = Column(db.String)
    date = Column(db.DateTime)
    lectures = db.relationship('Lecture', secondary=depositLectures)
