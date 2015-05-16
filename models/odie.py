#! /usr/bin/env python3

import app
import config
import models.documents

from app import db
from sqlalchemy.dialects import postgres


class OrderDocument(db.Model):
    __tablename__ = 'order_documents'
    __table_args__ = config.odie_table_args

    order_id = app.Column(db.Integer, db.ForeignKey('odie.orders.id'), primary_key=True)
    order = db.relationship('Order', backref=db.backref('items'))
    document_id = app.Column(db.ForeignKey('documents.documents.id'), primary_key=True)


class Order(db.Model):
    __tablename__ = 'orders'
    __table_args__ = config.odie_table_args

    id = app.Column(db.Integer, primary_key=True)
    name = app.Column(db.String(256))
    creation_time = app.Column(postgres.DATE, default=db.func.now())
    documents = db.relationship('Document', secondary='odie.order_documents')

