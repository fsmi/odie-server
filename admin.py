#! /usr/bin/env python3

import config

import datetime
import os

from odie import app, db
from api_utils import document_path, save_file
from models.documents import Document, Lecture, Examinant, Deposit

from flask_admin import Admin, BaseView, AdminIndexView
from flask_admin.form import FileUploadField
from flask_admin.contrib.sqla import ModelView
from flask.ext.login import current_user
from wtforms.validators import Optional

def _dateFormatter(attr_name):
    def f(v, c, m, n):
        d = getattr(m, attr_name)
        return d.date() if d else ''
    return f

class AuthViewMixin(BaseView):
    allowed_roles = config.ADMIN_PANEL_ALLOWED_GROUPS
    def is_accessible(self):
        return current_user.is_authenticated() \
                and any(True for perm in self.allowed_roles if current_user.has_permission(perm))

    def _handle_view(self, name, **kwargs):
        if not self.is_accessible():
            return self.render('unauthorized.html')

class AuthModelView(ModelView, AuthViewMixin):
    page_size = 50  # the default of 20 is a bit on the low side...

class AuthIndexView(AuthViewMixin, AdminIndexView):
    pass

class DocumentView(AuthModelView):

    def update_model(self, form, model):
        # We don't want flask-admin to handle the uploaded file, we'll do that ourselves.
        # however, Flask-Admin is welcome to handle the rest of the model update

        file = form.file
        # extra form fields are appended to the end of the form list, so we need to remove
        # the last element
        # pylint: disable=protected-access
        assert form._unbound_fields[-1][0] == 'file'
        form._unbound_fields = form._unbound_fields[:-1]
        delattr(form, 'file')

        success = super(DocumentView, self).update_model(form, model)
        if not success:
            return False

        if file.data:
            if model.file_id:
                # delete old file
                os.unlink(document_path(model.file_id))
            digest = save_file(file.data)
            model.file_id = digest

        if model.validation_time is None and form.validated:
            # document has just been validated
            model.validation_time = datetime.datetime.now()

        db.session.commit()
        return True


    list_template = 'document_list.html'
    edit_template = 'document_edit.html'
    form_excluded_columns = ('validation_time', 'file_id')
    form_extra_fields = {'file': FileUploadField()}
    form_args = {
        'comment': {'validators': [Optional()]},
    }
    column_list = (
        'id', 'lectures', 'examinants', 'date', 'number_of_pages', 'solution', 'comment',
        'document_type', 'validated', 'validation_time', 'submitted_by')
    column_filters = ('id', 'lectures', 'examinants', 'date', 'comment', 'document_type', 'submitted_by')
    column_labels = {
        'id': 'ID',
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
        'document_type': lambda v, c, m, n: DocumentView.doctype_labels[m.document_type],
        'solution': lambda v, c, m, n: DocumentView.solution_labels[m.solution],
        'date': _dateFormatter('date'),
        'validation_time': _dateFormatter('validation_time'),
    }

class LectureView(AuthModelView):
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
        'subject': lambda v, c, m, n: LectureView.subject_labels[m.subject],
    }
    column_labels = {
        'subject': 'Fach',
        'comment': 'Kommentar',
        'validated': 'Überprüft',
        'aliases': 'Aliase',
    }

class ExaminantView(AuthModelView):
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
        'price': lambda v, c, m, n: str(m.price) + ' €',
    }

admin = Admin(
    app,
    name='Odie (admin)',
    base_template='main.html',
    template_mode='bootstrap3',
    index_view=AuthIndexView(
        name='Home',
        template='main.html'))  # TODO: proper index view template

admin.add_view(DocumentView(Document, db.session, name='Dokumente'))
admin.add_view(LectureView(Lecture, db.session, name='Vorlesungen'))
admin.add_view(ExaminantView(Examinant, db.session, name='Prüfer'))
admin.add_view(DepositView(Deposit, db.session, name='Pfand'))
