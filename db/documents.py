#! /usr/bin/env python3

import config
import sqlalchemy

from odie import sqla, Column
from sqlalchemy.dialects import postgres


class Lecture(sqla.Model):
    __tablename__ = 'lectures'
    __table_args__ = config.documents_table_args

    id = Column(sqla.Integer, primary_key=True)
    name = Column(sqla.String)
    aliases = Column(postgres.ARRAY(sqla.String), server_default='{}')
    subject = Column(sqla.Enum('mathematics', 'computer science', 'both', 'other', name='subject', inherit_schema=True))
    comment = Column(sqla.String, server_default='')
    validated = Column(sqla.Boolean)

    def __str__(self):
        return self.name


lectureDocs = sqla.Table('lecture_docs',
        Column('lecture_id', sqla.Integer, sqla.ForeignKey('documents.lectures.id', ondelete='CASCADE')),
        Column('document_id', sqla.Integer, sqla.ForeignKey('documents.documents.id', ondelete='CASCADE')),
        **config.documents_table_args)

documentExaminants = sqla.Table('document_examinants',
        Column('document_id', sqla.Integer, sqla.ForeignKey('documents.documents.id', ondelete='CASCADE')),
        Column('examinant_id', sqla.Integer, sqla.ForeignKey('documents.examinants.id', ondelete='CASCADE')),
        **config.documents_table_args)


class Document(sqla.Model):
    __tablename__ = 'documents'
    __table_args__ = config.documents_table_args

    id = Column(sqla.Integer, primary_key=True)
    lectures = sqla.relationship('Lecture', secondary=lectureDocs,
            backref=sqla.backref('documents', lazy='dynamic'))
    examinants = sqla.relationship('Examinant', secondary=documentExaminants,
            backref=sqla.backref('documents', lazy='dynamic'))
    date = Column(sqla.DateTime(timezone=True))
    number_of_pages = Column(sqla.Integer, server_default='0')
    solution = Column(sqla.Enum('official', 'inofficial', 'none', name='solution', inherit_schema=True), nullable=True)
    comment = Column(sqla.String, server_default='')
    document_type = Column(sqla.Enum('oral', 'written', 'oral reexam', name='type', inherit_schema=True))
    has_file = Column(sqla.Boolean, server_default=sqlalchemy.sql.expression.false())
    validated = Column(sqla.Boolean)
    validation_time = Column(sqla.DateTime(timezone=True), nullable=True)
    submitted_by = Column(sqla.String, nullable=True)
    legacy_id = Column(sqla.Integer, nullable=True)  # old id from fs-deluxe, so we can recognize the old barcodes
    present_in_physical_folder = Column(sqla.Boolean, server_default=sqlalchemy.sql.expression.false())

    @property
    def examinants_names(self):
        return [ex.name for ex in self.examinants]

    @property
    def price(self):
        return config.FS_CONFIG['PRICE_PER_PAGE'] * self.number_of_pages



class Examinant(sqla.Model):
    __tablename__ = 'examinants'
    __table_args__ = config.documents_table_args

    id = Column(sqla.Integer, primary_key=True)
    name = Column(sqla.String)
    validated = Column(sqla.Boolean)

    def __str__(self):
        return self.name


depositLectures = sqla.Table('deposit_lectures',
        Column('deposit_id', sqla.Integer, sqla.ForeignKey('documents.deposits.id', ondelete='CASCADE')),
        Column('lecture_id', sqla.Integer, sqla.ForeignKey('documents.lectures.id', ondelete='CASCADE')),
        **config.documents_table_args)


class Deposit(sqla.Model):
    __tablename__ = 'deposits'
    __table_args__ = config.documents_table_args

    id = Column(sqla.Integer, primary_key=True)
    price = Column(sqla.Integer)
    name = Column(sqla.String)
    by_user = Column(sqla.String)
    date = Column(sqla.DateTime(timezone=True), server_default=sqla.func.now())
    lectures = sqla.relationship('Lecture', secondary=depositLectures)
