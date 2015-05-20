#! /usr/bin/env python3

import app
import config

from app import db
from sqlalchemy.dialects import postgres
from datetime import datetime as time

from models.documents import Document

class OrderDocument(db.Model):
    __tablename__ = 'order_documents'
    __table_args__ = config.odie_table_args

    index = app.Column(db.Integer, primary_key=True)
    order_id = app.Column(db.Integer, db.ForeignKey('odie.orders.id'), primary_key=True)
    order = db.relationship('Order', backref=db.backref('items', cascade='all', order_by=index))
    document_id = app.Column(db.ForeignKey('documents.documents.id'), primary_key=True)
    document = db.relationship('Document')


class Order(db.Model):
    __tablename__ = 'orders'
    __table_args__ = config.odie_table_args

    id = app.Column(db.Integer, primary_key=True)
    name = app.Column(db.String(256))
    creation_time = app.Column(postgres.DATE, default=db.func.now())

    def __init__(self, name, document_ids, creation_time=None):
        self.name = name
        self.creation_time = creation_time
        for idx, doc in enumerate(document_ids):
            OrderDocument(order=self, document_id=doc, index=idx)

    @property
    def documents(self):
        return [item.document for item in self.items]

