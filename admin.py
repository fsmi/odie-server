#! /usr/bin/env python3

from odie import app, db
from models.documents import Document, Lecture, Examinant, Deposit

from flask import redirect
from flask_admin import Admin, BaseView, AdminIndexView
from flask_admin.contrib.sqla import ModelView
from flask.ext.login import current_user
from wtforms.validators import Optional

import datetime

def _dateFormatter(attr_name):
    def f(v, c, m, n):
        d = getattr(m, attr_name)
        return d.date() if d else ''
    return f

_exam_allowed_roles = ['adm', 'info_protokolle', 'info_klausuren', 'mathe_protokolle', 'mathe_klausuren']

class AuthView(BaseView):
    def is_accessible(self):
        return current_user.is_authenticated() \
                and any(True for perm in self.allowed_roles if current_user.has_permission(perm))

    def _handle_view(self, name, **kwargs):
        if not self.is_accessible():
            return redirect('/')

class AuthModelView(ModelView, AuthView):
    pass


class DocumentView(AuthModelView):
    allowed_roles = _exam_allowed_roles
    list_template = 'document_list.html'
    form_excluded_columns = ('validation_time', 'file_id')
    form_args = {
            'comment': {'validators': [Optional()]},
        }
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

    def on_model_change(self, form, model, is_created):
        if model.validation_time is None and model.validated:
            # document has just been validated
            model.validation_time = datetime.datetime.now()

class LectureView(AuthModelView):
    allowed_roles = _exam_allowed_roles
    form_excluded_columns = ('documents',)
    form_args = {
            'comment': {'validators': [Optional()]},
        }
    subject_labels = {
            'computer science': 'Informatik',
            'mathematics': 'Mathematik',
            'both': 'Beides',
        }
    column_formatters = {
            'subject': lambda v,c,m,n: LectureView.subject_labels[m.subject],
        }
    column_labels = {
            'subject': 'Fach',
            'comment': 'Kommentar',
            'validated': 'Überprüft',
            'aliases': 'Aliase',
        }

class ExaminantView(AuthModelView):
    allowed_roles = _exam_allowed_roles
    form_excluded_columns = ('documents',)
    column_labels = {
            'validated': 'Überprüft',
        }

class DepositView(AuthModelView):
    allowed_roles = ['adm']
    column_labels = {
            'price': 'Geldwert',
            'by_user': 'Eingetragen von',
            'date': 'Datum',
            'lectures': 'Vorlesungen',
        }
    column_formatters = {
            'date': _dateFormatter('date'),
            'price': lambda v,c,m,n: str(m.price) + ' €',
        }

docView = DocumentView(Document, db.session, name='Dokumente')
admin = Admin(app, name='Odie (admin)', base_template='main.html')

admin.add_view(docView)
admin.add_view(LectureView(Lecture, db.session, name='Vorlesungen'))
admin.add_view(ExaminantView(Examinant, db.session, name='Prüfer'))
admin.add_view(DepositView(Deposit, db.session, name='Pfand'))
