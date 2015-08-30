#! /usr/bin/env python3

import config

from odie import sqla, Column

class OrderDocument(sqla.Model):
    __tablename__ = 'order_documents'
    __table_args__ = config.odie_table_args

    index = Column(sqla.Integer, primary_key=True)
    order_id = Column(sqla.Integer, sqla.ForeignKey('odie.orders.id'), primary_key=True)
    order = sqla.relationship('Order', backref=sqla.backref('items', cascade='all', order_by=index, lazy='subquery'))
    document_id = Column(sqla.ForeignKey('documents.documents.id', ondelete='CASCADE'), primary_key=True)
    document = sqla.relationship('Document', lazy='joined')


class Order(sqla.Model):
    __tablename__ = 'orders'
    __table_args__ = config.odie_table_args

    id = Column(sqla.Integer, primary_key=True)
    name = Column(sqla.String(256))
    creation_time = Column(sqla.DateTime(timezone=True), server_default=sqla.func.now())

    def __init__(self, name, document_ids, creation_time=None):
        self.name = name
        self.creation_time = creation_time
        for idx, doc in enumerate(document_ids):
            OrderDocument(order=self, document_id=doc, index=idx)

    @property
    def documents(self):
        return [item.document for item in self.items]
