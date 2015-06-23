#! /usr/bin/env python3

from odie import admin, db
from models.documents import Document, Lecture, Examinant, Deposit

from flask import redirect
from flask_admin import BaseView
from flask_admin.contrib.sqla import ModelView
from flask.ext.login import current_user

import datetime

class AuthView(BaseView):
    def is_accessible(self):
        return current_user.is_authenticated()

    def _handle_view(self, name, **kwargs):
        if not self.is_accessible():
            return redirect('/')

class AuthModelView(ModelView, AuthView):
    pass

class DocumentView(AuthModelView):
    form_excluded_columns = ('validation_time', 'file_id')

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

