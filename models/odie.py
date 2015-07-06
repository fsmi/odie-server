#! /usr/bin/env python3

import config

from odie import db, Column

from models.documents import Document

class OrderDocument(db.Model):
    __tablename__ = 'order_documents'
    __table_args__ = config.odie_table_args

    index = Column(db.Integer, primary_key=True)
    order_id = Column(db.Integer, db.ForeignKey('odie.orders.id'), primary_key=True)
    order = db.relationship('Order', backref=db.backref('items', cascade='all', order_by=index))
    document_id = Column(db.ForeignKey('documents.documents.id', ondelete='CASCADE'), primary_key=True)
    document = db.relationship('Document')


class Order(db.Model):
    __tablename__ = 'orders'
    __table_args__ = config.odie_table_args

    id = Column(db.Integer, primary_key=True)
    name = Column(db.String(256))
    creation_time = Column(db.DateTime(timezone=True), server_default=db.func.now())

    def __init__(self, name, document_ids, creation_time=None):
        self.name = name
        self.creation_time = creation_time
        for idx, doc in enumerate(document_ids):
            OrderDocument(order=self, document_id=doc, index=idx)

    @property
    def documents(self):
        docs = Document.query.filter(Document.id.in_([it.document_id for it in self.items])).all()
        docs_by_id = {doc.id: doc for doc in docs}
        return [docs_by_id[it.document_id] for it in self.items]

