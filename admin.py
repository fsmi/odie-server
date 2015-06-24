#! /usr/bin/env python3

from odie import admin, db
from models.documents import Document, Lecture, Examinant, Deposit

from flask import redirect
from flask_admin import BaseView
from flask_admin.contrib.sqla import ModelView
from flask.ext.login import current_user

import datetime

def _dateFormatter(attr_name):
    def f(v, c, m, n):
        d = getattr(m, attr_name)
        return d.date() if d else ''
    return f

class AuthView(BaseView):
    def is_accessible(self):
        return current_user.is_authenticated()

    def _handle_view(self, name, **kwargs):
        if not self.is_accessible():
            return redirect('/')

class AuthModelView(ModelView, AuthView):
    pass


class DocumentView(AuthModelView):
    list_template = 'document_list.html'
    form_excluded_columns = ('validation_time', 'file_id')
    column_list = (
            'lectures', 'examinants', 'date', 'number_of_pages', 'solution', 'comment',
            'document_type', 'validated', 'validation_time', 'submitted_by')
    column_labels = {
            'lectures': 'Vorlesungen',
            'examinants': 'Prüfer',
            'date': 'Datum',
            'number_of_pages': 'Seiten',
            'solution': 'Lösung',
            'comment': 'Kommentar',
            'document_type': 'Typ',
            'validated': 'Überprüft',
            'validation_time': 'Überprüft am',
            'submitted_by': 'Von',
        }
    doctype_labels = {
            'oral': 'Mündl.',
            'written': 'Schriftl.',
            'oral reexam': 'Nachprüfung',
        }
    solution_labels = {
            'official': 'Ja (offiziell)',
            'inofficial': 'Ja (Studi)',
            'none': 'Nein',
            None: '?',
        }
    column_formatters = {
            'document_type': lambda v,c,m,n: DocumentView.doctype_labels[m.document_type],
            'solution': lambda v,c,m,n: DocumentView.solution_labels[m.solution],
            'date': _dateFormatter('date'),
            'validation_time': _dateFormatter('validation_time'),
        }
    def scaffold_list_form(self, validators=[], **kwargs):
        validators = {'name': {'validators': []}}
        return super(DocumentView, self).scaffold_list_form(validators=validators, **kwargs)

    def on_model_change(self, form, model, is_created):
        if model.validation_time is None and model.validated:
            # document has just been validated
            model.validation_time = datetime.datetime.now()

class LectureView(AuthModelView):
    form_excluded_columns = ('documents',)

class ExaminantView(AuthModelView):
    form_excluded_columns = ('documents',)

admin.add_view(DocumentView(Document, db.session, name='Dokumente'))
admin.add_view(LectureView(Lecture, db.session, name='Vorlesungen'))
admin.add_view(ExaminantView(Examinant, db.session, name='Prüfer'))
admin.add_view(AuthModelView(Deposit, db.session, name='Pfand'))
