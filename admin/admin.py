#! /usr/bin/env python3

import barcode
import config

import datetime
import os

from odie import app, sqla
from api_utils import document_path, save_file
from db.documents import Document, Lecture, Examinant, Deposit
from .fields import ViewButton, UnvalidatedList

from flask import redirect, url_for
from flask_admin import Admin, BaseView, AdminIndexView, expose
from flask_admin.form import FileUploadField
from flask_admin.contrib.sqla import ModelView
from flask.ext.login import current_user
from sqlalchemy.inspection import inspect
from sqlalchemy.orm.properties import RelationshipProperty
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
            return self.render('unauthorized.html', login_page=config.FS_CONFIG['LOGIN_PAGE'])


class AuthModelView(ModelView, AuthViewMixin):
    page_size = 50  # the default of 20 is a bit on the low side...

    def _log_model_changes(self, model, state):

        if state == 'changed' and not sqla.session.is_modified(model):
            return

        msg = '{} {} by {}\n\n'.format(model.__class__.__name__, state, current_user.full_name)
        view = model_views[model.__class__]
        attrs = inspect(model).attrs
        for (col, _) in self.get_list_columns():
            attr = attrs[col]
            prop = model.__class__.__mapper__.attrs[col]
            changed = state == 'changed' and attr.history.has_changes()
            if changed and isinstance(attr.value, datetime.datetime):
                # special case: convert attr.value from naive to aware datetime
                val = attr.value.replace(tzinfo=attr.history.deleted[0].tzinfo)
                changed = val != attr.history.deleted[0]

            if changed:
                if isinstance(prop, RelationshipProperty):
                    msg += '**{}: {}**\n'.format(attr.key, ', '.join(
                        list(map(str, attr.history.unchanged)) +
                        ['-{}'.format(val) for val in attr.history.deleted] +
                        ['+{}'.format(val) for val in attr.history.added]
                    ))
                else:
                    msg += '**{}: {} -> {}**\n'.format(
                        attr.key, attr.history.deleted[0], attr.history.added[0]
                    )
            else:
                if isinstance(prop, RelationshipProperty):
                    msg += '{}: {}\n'.format(attr.key, ', '.join(map(str, attr.value)))
                else:
                    msg += '{}: {}\n'.format(attr.key, attr.value)

        if state != 'deleted':
            msg += '\n' + url_for(view.endpoint + '.edit_view', id=model.id, _external=True)

        config.log_admin_audit(msg)

    def on_model_change(self, form, model, is_created):
        self._log_model_changes(model, 'created' if is_created else 'changed')

    def delete_model(self, model):
        self._log_model_changes(model, 'deleted')
        return super().delete_model(model)


class ClientRedirectView(BaseView):
    @expose('/')
    def index(self):
        return redirect(url_for('.index') + '../../web/')

class AuthIndexView(AuthViewMixin, AdminIndexView):
    # This is the only way I could find to make the Home tab de facto disappear:
    # name it '' and redirect to somewhere else.
    # Note that simply giving Admin a different View as index_view doesn't work
    # without copying some of the internals of AdminIndexView, which I want to avoid
    def __init__(self):
        super().__init__()
        self.name = ''

    @expose('/')
    def index(self):
        # automatically redirect to document listing
        return redirect(url_for('document.index_view'))

class DocumentView(AuthModelView):

    def delete_model(self, model):
        super().delete_model(model)
        if model.has_file:
            os.unlink(document_path(model.id))


    def _hide_file_upload(self, form):
        # We don't want flask-admin to handle the uploaded file, we'll do that ourselves.
        # however, Flask-Admin is welcome to handle the rest of the model update

        file = form.file
        # extra form fields are appended to the end of the form list, so we need to remove
        # the last element
        # pylint: disable=protected-access
        assert form._unbound_fields[-1][0] == 'file'
        form._unbound_fields = form._unbound_fields[:-1]
        delattr(form, 'file')
        return file

    def _handle_file_upload(self, file, form, model):
        got_new_file = False
        if file.data:
            if model.has_file:
                # delete old file
                os.unlink(document_path(model.id))
            save_file(model, file.data)
            if form.validated.data:
                got_new_file = True

        if model.validation_time is None and form.validated.data:
            # document has just been validated for the first time
            model.validation_time = datetime.datetime.now()
            got_new_file = True

        if got_new_file:
            if model.document_type != 'written':
                barcode.bake_barcode(model)
            config.document_validated(document_path(model.id))

    def update_model(self, form, model):
        file = self._hide_file_upload(form)
        success = super().update_model(form, model)
        if not success:
            return False
        self._handle_file_upload(file, form, model)
        sqla.session.commit()
        return True

    def create_model(self, form):
        file = self._hide_file_upload(form)
        model = super().create_model(form)
        if not model:
            return model
        self._handle_file_upload(file, form, model)
        sqla.session.commit()
        return model


    list_template = 'document_list.html'
    form_edit_rules = [
        'lectures',
        UnvalidatedList('lectures', 'lecture.edit_view'),
        'examinants',
        UnvalidatedList('examinants', 'examinant.edit_view'),
        'date',
        'solution',
        'document_type',
        'number_of_pages',
        'comment',
        'present_in_physical_folder',
        'validated',
        'submitted_by',
        'file',
        ViewButton(),
    ]
    form_excluded_columns = ('validation_time', 'has_file', 'legacy_id')  # this isn't strictly necessary, but it shuts up a warning
    form_extra_fields = {'file': FileUploadField()}
    form_args = {
        'comment': {'validators': [Optional()]},
        'number_of_pages': {'validators': [Optional()]},
    }
    column_list = (
        'id', 'lectures', 'examinants', 'date', 'number_of_pages', 'solution', 'comment',
        'document_type', 'present_in_physical_folder', 'validated', 'validation_time', 'submitted_by')
    column_filters = ('id', 'lectures', 'examinants', 'date', 'comment', 'document_type', 'present_in_physical_folder', 'validated', 'validation_time', 'submitted_by')
    column_labels = {
        'id': 'ID',
        'lectures': 'Vorlesungen',
        'examinants': 'Prüfer',
        'date': 'Datum',
        'number_of_pages': 'Seiten',
        'solution': 'Lösung',
        'comment': 'Kommentar',
        'document_type': 'Typ',
        'present_in_physical_folder': 'Ausgedruckt für Präsenzordner',
        'validated': 'Überprüft',
        'validation_time': 'Überprüft am',
        'submitted_by': 'Von',
    }
    doctype_labels = {
        'oral': 'Mündl.',
        'written': 'Schriftl.',
        'oral reexam': 'Nachprüfung',
    }

    def format_solution(v, c, model, n):
        if model.document_type == 'written':
            return {
                'official': 'Ja (offiziell)',
                'inofficial': 'Ja (Studi)',
                'none': 'Nein',
                None: '?',
            }[model.solution]
        return ''

    column_formatters = {
        'document_type': lambda v, c, m, n: DocumentView.doctype_labels[m.document_type],
        'solution': format_solution,
        'date': _dateFormatter('date'),
        'validation_time': _dateFormatter('validation_time'),
    }

class LectureView(AuthModelView):
    form_excluded_columns = ('documents',)
    form_args = {
        'comment': {'validators': [Optional()]},
        'aliases': {'validators': [Optional()]},
    }
    subject_labels = {
        'computer science': 'Informatik',
        'mathematics': 'Mathematik',
        'both': 'Beides',
        'other': 'Anderes (Ergänzungsfach)',
    }
    column_formatters = {
        'subject': lambda v, c, m, n: LectureView.subject_labels[m.subject],
    }
    column_labels = {
        'subject': 'Fach',
        'comment': 'Öffentlicher Kommentar (HTML)',
        'validated': 'Überprüft',
        'aliases': 'Aliase',
    }
    column_filters = ('id', 'name', 'subject', 'validated')
    column_searchable_list = ['name']

class ExaminantView(AuthModelView):
    form_excluded_columns = ('documents',)
    column_labels = {
        'validated': 'Überprüft',
    }
    column_filters = ('id', 'name', 'validated')
    column_searchable_list = ['name']

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
    column_searchable_list = ['name']

admin = Admin(
    app,
    name='Odie (admin)',
    base_template='main.html',
    template_mode='bootstrap3',
    index_view=AuthIndexView())

model_views = {
    Document: DocumentView(Document, sqla.session, name='Dokumente'),
    Lecture: LectureView(Lecture, sqla.session, name='Vorlesungen'),
    Examinant: ExaminantView(Examinant, sqla.session, name='Prüfer'),
    Deposit: DepositView(Deposit, sqla.session, name='Pfand'),
}

admin.add_view(ClientRedirectView(name='Zurück zu Odie'))
for view in model_views.values():
    admin.add_view(view)
