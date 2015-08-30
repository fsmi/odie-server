#! /usr/bin/env python3

import barcode
import config

import collections
import datetime
import os

from odie import app, sqla
from api_utils import document_path, save_file
from db.documents import Document, Lecture, Examinant, Deposit, Folder
from db.garfield import Location
from .fields import ViewButton, UnvalidatedList

from flask import redirect, request, url_for
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
        if isinstance(d, datetime.datetime):
            d = d.date()
        return d if d else ''
    return f

class AuthViewMixin(BaseView):
    allowed_roles = config.ADMIN_PANEL_ALLOWED_GROUPS

    def is_accessible(self):
        return current_user.is_authenticated() and current_user.has_permission(*self.allowed_roles)

    def inaccessible_callback(self, name, **kwargs):
        return self.render(
                'unauthorized.html',
                login_page=config.FS_CONFIG['LOGIN_PAGE'],
                target_paras='&'.join('{}={}'.format(k, v) for k, v in request.args.items()),
                target_path=request.script_root + request.path)


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
            is_list = isinstance(prop, RelationshipProperty) and prop.uselist
            changed = state == 'changed' and attr.history.has_changes()
            if changed and isinstance(attr.value, datetime.datetime):
                # special case: convert attr.value from naive to aware datetime
                val = attr.value.replace(tzinfo=attr.history.deleted[0].tzinfo)
                changed = val != attr.history.deleted[0]

            if changed:
                if is_list:
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
                if is_list:
                    msg += '{}: {}\n'.format(attr.key, ', '.join(map(str, attr.value)))
                else:
                    msg += '{}: {}\n'.format(attr.key, attr.value)

        if state != 'deleted':
            msg += '\n' + url_for(view.endpoint + '.edit_view', id=model.id, _external=True)

        config.log_admin_audit(self, model, msg)

    def on_model_change(self, form, model, is_created):
        self._log_model_changes(model, 'created' if is_created else 'changed')

    def delete_model(self, model):
        self._log_model_changes(model, 'deleted')
        return super().delete_model(model)


# obviously this won't work when running locally, as client and server won't share an origin, but it's still nice to have
class ClientRedirectView(BaseView):
    @expose('/')
    def index(self):
        return redirect(url_for('.index') + '../../web/')

class PrintForFolderView(AuthViewMixin):
    allowed_roles = ['info_protokolle', 'mathe_protokolle']

    def _query_unprinted(self, folder):
        q = Document.query.filter_by(document_type=folder.document_type)
        q = q.filter(~Document.printed_in.contains(folder))
        if folder.examinants:
            q = q.filter(Document.examinants.any(Examinant.folders.contains(folder)))
        if folder.lectures:
            q = q.filter(Document.lectures.any(Lecture.folders.contains(folder)))
        return q

    def _get_location(self):
        # Nobody would ever be a member of both groups at the same time, right?
        if current_user.has_permission('info_protokolle'):
            return 'FSI'
        if current_user.has_permission('mathe_protokolle'):
            return 'FSM'

    def _get_folders_with_counts(self):
        for folder in Folder.query.filter(Location.name == self._get_location()).order_by(Folder.name).all():
            count = self._query_unprinted(folder).count()
            if count:
                yield (folder, count)

    @expose('/')
    def index(self):
        return self.render('print_for_folder.html',
                           folders=self._get_folders_with_counts(),
                           examinants_without_folders=Examinant.query.filter(~Examinant.folders.any()).order_by(Examinant.name).all())

    @expose('/print-all', methods=['POST'])
    def print_all(self):
        folders = list(self._get_folders_with_counts())
        for folder, _ in folders:
            documents = self._query_unprinted(folder).all()
            config.print_documents(
                doc_paths=[document_path(doc.id) for doc in documents],
                cover_text=None,
                printer=config.FS_CONFIG['OFFICES'][self._get_location()]['printers'][0],
                usercode=config.PRINTER_USERCODES['internal']
            )
            folder.printed_docs += documents
            sqla.session.commit()

        return self.render('print_for_folder.html',
                           printed_folders=folders,
                           examinants_without_folders=Examinant.query.filter(~Examinant.folders.any()).sort_by(Examinant.name).all())


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
        if model.has_file and os.path.exists(document_path(model.id)) and not app.config['DEBUG']:
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
            if model.has_file and os.path.exists(document_path(model.id)) and not app.config['DEBUG']:
                # delete old file
                os.unlink(document_path(model.id))
            save_file(model, file.data)
            if model.validated:
                got_new_file = True

        if model.validation_time is None and model.validated:
            # document has just been validated for the first time
            model.validation_time = datetime.datetime.now()
            got_new_file = True

        if got_new_file:
            if model.document_type != 'written':
                barcode.bake_barcode(model)
            config.document_validated(document_path(model.id))

    def on_model_change(self, form, model, is_created):
        if is_created:
            model.validated = True

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
    # no number_of_pages, validated or submitted_by
    form_create_rules = [
        'document_type',
        'department',
        'lectures',
        'examinants',
        'date',
        'solution',
        'comment',
        'file',
    ]
    form_edit_rules = [
        'document_type',
        'department',
        'lectures',
        UnvalidatedList('lectures', 'lecture.edit_view'),
        'examinants',
        UnvalidatedList('examinants', 'examinant.edit_view'),
        'date',
        'solution',
        'number_of_pages',
        'comment',
        'validated',
        'submitted_by',
        'file',
        ViewButton(),
    ]
    form_excluded_columns = ('validation_time', 'has_file', 'legacy_id', 'printed_in')  # this isn't strictly necessary, but it shuts up a warning
    form_extra_fields = {'file': FileUploadField()}
    form_args = {
        'comment': {'validators': [Optional()]},
        'number_of_pages': {'validators': [Optional()]},
    }
    column_list = (
        'id', 'department', 'lectures', 'examinants', 'date', 'number_of_pages', 'solution', 'comment',
        'document_type', 'validated', 'validation_time', 'submitted_by')
    column_filters = ('id', 'department', 'lectures', 'examinants', 'date', 'solution', 'comment', 'document_type', 'validated', 'validation_time', 'submitted_by')
    column_labels = {
        'id': 'ID',
        'department': 'Fakultät',
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
    department_labels = {
        'computer science': 'Informatik',
        'mathematics': 'Mathematik',
        'other': 'Andere (Ergänzungsfach)',
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
        'department': lambda v, c, m, n: DocumentView.department_labels[m.department],
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
    column_labels = {
        'comment': 'Öffentlicher Kommentar (HTML)',
        'validated': 'Überprüft',
        'aliases': 'Aliase',
    }
    column_filters = ('id', 'name', 'validated')
    column_searchable_list = ['name']

class ExaminantView(AuthModelView):
    form_excluded_columns = ('documents',)
    column_labels = {
        'validated': 'Überprüft',
    }
    column_filters = ('id', 'name', 'validated')
    column_searchable_list = ['name']

class FolderView(AuthModelView):
    form_excluded_columns = ('printed_docs',)
    column_labels = {
        'location': 'Ort',
        'document_type': 'Dokumententyp',
        'examinants': 'Prüfer',
        'lectures': 'Vorlesungen'
    }

class DepositView(AuthModelView):
    allowed_roles = ['kasse', 'adm']
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

model_views = collections.OrderedDict([
    (Document, DocumentView(Document, sqla.session, name='Dokumente')),
    (Lecture, LectureView(Lecture, sqla.session, name='Vorlesungen')),
    (Examinant, ExaminantView(Examinant, sqla.session, name='Prüfer')),
    (Folder, FolderView(Folder, sqla.session, name='Ordner')),
    (Deposit, DepositView(Deposit, sqla.session, name='Pfand')),
])

admin.add_view(ClientRedirectView(name='Zurück zu Odie'))
for view in model_views.values():
    admin.add_view(view)
admin.add_view(PrintForFolderView(name='Protokolle für Ordner ausdrucken'))
