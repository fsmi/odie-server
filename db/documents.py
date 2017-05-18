#! /usr/bin/env python3

import config
import sqlalchemy
import datetime

from odie import sqla, Column
from sqlalchemy.dialects import postgres
from sqlalchemy import func
from sqlalchemy.orm import column_property
from db import garfield
from pytz import reference


lecture_docs = sqla.Table('lecture_docs',
        Column('lecture_id', sqla.Integer, sqla.ForeignKey('documents.lectures.id', ondelete='CASCADE')),
        Column('document_id', sqla.Integer, sqla.ForeignKey('documents.documents.id', ondelete='CASCADE')),
        **config.documents_table_args)

folder_lectures = sqla.Table('folder_lectures',
        Column('folder_id', sqla.Integer, sqla.ForeignKey('documents.folders.id', ondelete='CASCADE')),
        Column('lecture_id', sqla.Integer, sqla.ForeignKey('documents.lectures.id', ondelete='CASCADE')),
        **config.documents_table_args)


class Lecture(sqla.Model):
    __tablename__ = 'lectures'
    __table_args__ = config.documents_table_args

    id = Column(sqla.Integer, primary_key=True)
    name = Column(sqla.String)
    aliases = Column(postgres.ARRAY(sqla.String), server_default='{}')
    comment = Column(sqla.String, server_default='')
    validated = Column(sqla.Boolean)

    documents = sqla.relationship('Document', secondary=lecture_docs, lazy='dynamic', back_populates='lectures')
    folders = sqla.relationship('Folder', secondary=folder_lectures, back_populates='lectures')

    early_document_until = column_property(
        func.garfield.lecture_early_document_reward_until(id,config.FS_CONFIG['EARLY_DOCUMENT_COUNT'])
    )

    '''
-- the following function returns the early document reward deadline for a given lecture.
    TODO implement +x days grace period
SET search_path = garfield;
CREATE OR REPLACE FUNCTION lecture_early_document_reward_until(lec_id int, early_document_count int) RETURNS timestamptz AS $$
DECLARE
	result timestamptz;
BEGIN
	LOCK TABLE documents.lectures, documents.documents, documents.lecture_docs IN SHARE MODE;
	IF NOT exists(select 1 from documents.lectures where id=lec_id) THEN
		RAISE EXCEPTION 'Lecture % does not exist', lec_id;
	END IF;
	IF early_document_count = 0 THEN
		return null;
	END IF;

	select doc.validation_time into result
	from documents.documents as doc
	join documents.lecture_docs as jt on jt.document_id = doc.id
	join documents.lectures as lec on jt.lecture_id = lec.id
	where doc.validation_time is not null
	and lec.id = lec_id
	and doc.validated = true
	--and lec.validated = true
	order by doc.validation_time ASC
	limit 1 offset (early_document_count-1);
	IF NOT FOUND THEN
		return null;
	END IF;

	return result;

END
$$ LANGUAGE plpgsql SECURITY DEFINER SET search_path = garfield, pg_temp;
    '''


    @property
    def early_document_eligible(self):
        until = self.early_document_until
        return until is None or datetime.datetime.now(reference.LocalTimezone()) <= until



    def __str__(self):
        return self.name


document_examinants = sqla.Table('document_examinants',
        Column('document_id', sqla.Integer, sqla.ForeignKey('documents.documents.id', ondelete='CASCADE')),
        Column('examinant_id', sqla.Integer, sqla.ForeignKey('documents.examinants.id', ondelete='CASCADE')),
        **config.documents_table_args)

folder_docs = sqla.Table('folder_docs',
        Column('folder_id', sqla.Integer, sqla.ForeignKey('documents.folders.id', ondelete='CASCADE')),
        Column('document_id', sqla.Integer, sqla.ForeignKey('documents.documents.id', ondelete='CASCADE')),
        **config.documents_table_args)


document_type = sqla.Enum('oral', 'written', 'oral reexam', name='document_type', inherit_schema=True)


class Document(sqla.Model):
    __tablename__ = 'documents'
    __table_args__ = config.documents_table_args

    id = Column(sqla.Integer, primary_key=True)
    department = Column(sqla.Enum('mathematics', 'computer science', 'other', name='department', inherit_schema=True))
    date = Column(sqla.Date())
    number_of_pages = Column(sqla.Integer, server_default='0')
    solution = Column(sqla.Enum('official', 'inofficial', 'none', name='solution', inherit_schema=True), nullable=True)
    comment = Column(sqla.String, server_default='')
    document_type = Column(document_type)
    has_file = Column(sqla.Boolean, server_default=sqlalchemy.sql.expression.false())
    validated = Column(sqla.Boolean)
    has_barcode = Column(sqla.Boolean, server_default=sqlalchemy.sql.expression.false())
    validation_time = Column(sqla.DateTime(timezone=True), nullable=True)
    submitted_by = Column(sqla.String, nullable=True)
    legacy_id = Column(sqla.Integer, nullable=True)  # old id from fs-deluxe, so we can recognize the old barcodes
    early_document_eligible = Column(sqla.Boolean, nullable=False, server_default=sqlalchemy.sql.expression.false())
    deposit_return_eligible = Column(sqla.Boolean, nullable=False, server_default=sqlalchemy.sql.expression.false())

    lectures = sqla.relationship('Lecture', secondary=lecture_docs, back_populates='documents')
    examinants = sqla.relationship('Examinant', secondary=document_examinants, back_populates='documents')
    printed_in = sqla.relationship('Folder', secondary=folder_docs, back_populates='printed_docs')

    @property
    def examinants_names(self):
        return [ex.name for ex in self.examinants]

    @property
    def price(self):
        return config.FS_CONFIG['PRICE_PER_PAGE'] * self.number_of_pages


folder_examinants = sqla.Table('folder_examinants',
        Column('folder_id', sqla.Integer, sqla.ForeignKey('documents.folders.id', ondelete='CASCADE')),
        Column('examinant_id', sqla.Integer, sqla.ForeignKey('documents.examinants.id', ondelete='CASCADE')),
        **config.documents_table_args)


class Examinant(sqla.Model):
    __tablename__ = 'examinants'
    __table_args__ = config.documents_table_args

    id = Column(sqla.Integer, primary_key=True)
    name = Column(sqla.String)
    validated = Column(sqla.Boolean)

    documents = sqla.relationship('Document', secondary=document_examinants, lazy='dynamic', back_populates='examinants')
    folders = sqla.relationship('Folder', secondary=folder_examinants, back_populates='examinants')

    def __str__(self):
        return self.name


class Folder(sqla.Model):
    __tablename__ = 'folders'
    __table_args__ = config.documents_table_args

    id = Column(sqla.Integer, primary_key=True)
    name = Column(sqla.String)
    location_id = Column(sqla.Integer, sqla.ForeignKey(garfield.Location.id))
    document_type = Column(document_type)

    location = sqla.relationship(garfield.Location, lazy='joined', uselist=False, back_populates='folders')
    examinants = sqla.relationship('Examinant', secondary=folder_examinants, lazy='subquery', back_populates='folders')
    lectures = sqla.relationship('Lecture', secondary=folder_lectures, lazy='subquery', back_populates='folders')
    printed_docs = sqla.relationship('Document', secondary=folder_docs, back_populates='printed_in')

    def __str__(self):
        return self.name


deposit_lectures = sqla.Table('deposit_lectures',
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

    lectures = sqla.relationship('Lecture', secondary=deposit_lectures)
