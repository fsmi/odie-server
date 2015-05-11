#! /usr/bin/env python3

import app
import config
import models.documents

from app import db
from sqlalchemy.dialects import postgres


class CartDocument(db.Model):
    __tablename__ = 'cart_documents'
    __table_args__ = config.odie_table_args

    cart_id = app.Column(db.Integer, db.ForeignKey('odie.carts.id'), primary_key=True)
    cart = db.relationship('Cart', backref=db.backref('items'))
    document_id = app.Column(db.ForeignKey('documents.documents.id'), primary_key=True)


class Cart(db.Model):
    __tablename__ = 'carts'
    __table_args__ = config.odie_table_args

    id = app.Column(db.Integer, primary_key=True)
    name = app.Column(db.String(256))
    creation_time = app.Column(postgres.DATE, default=db.func.now())
    documents = db.relationship('Document', secondary='odie.cart_documents')

