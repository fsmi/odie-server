#! /usr/bin/env python3

import barcode
import config
import datetime
import json
import os

from flask import request, send_file
from marshmallow import Schema, fields
from marshmallow.validate import OneOf
from sqlalchemy.orm import subqueryload
from sqlalchemy.orm.exc import NoResultFound
from pytz import reference

from .common import IdSchema, DocumentDumpSchema
from odie import app, sqla, csrf, ClientError
from login import login_required, get_user, is_kiosk, unauthorized
from api_utils import endpoint, api_route, handle_client_errors, document_path, number_of_pages, save_file, serialize, event_stream
from db.documents import Lecture, Document, Examinant, PaymentState


@app.route('/api/scanner/<location>/<int:id>')
@login_required
@event_stream
def scanner(location, id):
    assert location in config.FS_CONFIG['OFFICES']
    assert 0 <= id <= len(config.LASER_SCANNERS[location])
    (host, port) = config.LASER_SCANNERS[location][id]
    bs = barcode.BarcodeScanner(host, port, get_user().first_name)
    schema = DocumentDumpSchema()  # __init__ requires application context
    yield None  # exit application context, start event stream

    for doc in bs:
        if doc is None:
            # socket read has timeouted, try to write to output stream
            yield (None, None)
        else:
            yield (None, serialize(doc, lambda: schema))


class LectureDumpSchema(IdSchema):
    name = fields.Str()
    aliases = fields.List(fields.Str())
    comment = fields.Str()
    validated = fields.Boolean()
    early_document_until = fields.LocalDateTime()
    early_document_eligible = fields.Boolean()

api_route('/api/lectures')(
endpoint(
        schemas={'GET': LectureDumpSchema},
        query_fn=lambda: Lecture.query,
        paginate_many=False)
)


class ExaminantSchema(IdSchema):
    name = fields.Str()
    validated = fields.Boolean()


api_route('/api/examinants')(
endpoint(
        schemas={'GET': ExaminantSchema},
        query_fn=lambda: Examinant.query,
        paginate_many=False)
)


def documents_query():
    q = Document.query.options(subqueryload('lectures'), subqueryload('examinants'))
    filters = json.loads(request.args.get('filters', '{}'))
    for id in filters.get('includes_lectures', []):
        q = q.filter(Document.lectures.any(Lecture.id == id))
    for id in filters.get('includes_examinants', []):
        q = q.filter(Document.examinants.any(Examinant.id == id))
    return q

api_route('/api/documents')(
endpoint(
        schemas={'GET': DocumentDumpSchema},
        query_fn=documents_query)
)

# aggregate values of unpaginated source data
@api_route('/api/documents/meta')
def documents_metadata():
    q = documents_query()
    return {
        'total_written': q.filter_by(document_type='written').count(),
        'total_oral': q.filter_by(document_type='oral').count(),
        'total_oral_reexam': q.filter_by(document_type='oral reexam').count(),
    }


class DocumentLoadSchema(Schema):  # used by document submission
    department = fields.Str(required=True, validate=OneOf(['computer science', 'mathematics', 'other']))
    lectures = fields.List(fields.Str(), required=True)
    examinants = fields.List(fields.Str(), required=True)
    date = fields.Date(required=True)
    document_type = fields.Str(required=True, validate=lambda x: get_user() and x == 'written' or x in ['oral', 'oral reexam'])
    student_name = fields.Str(required=False, allow_none=True)

class FullDocumentLoadSchema(DocumentLoadSchema):
    # unfortunately the combination (required==False, validate is not None) is not supported by marshmallow
    # So we need to perform additional validation in the route
    solution = fields.Str(required=False)
    comment = fields.Str(required=False)


def _allowed_file(filename):
    return os.path.splitext(filename)[1] in config.SUBMISSION_ALLOWED_FILE_EXTENSIONS


@api_route('/api/documents', methods=['POST'])
@csrf.exempt
def submit_document_external():
    knows_what_they_are_doing = get_user() and get_user().has_permission(
            'info_protokolle',
            'info_klausuren',
            'mathe_protokolle',
            'mathe_klausuren')
    return submit_documents(validated=bool(knows_what_they_are_doing))


def _match_lectures(lecture_names, validated):
    lectures = []
    for lect in lecture_names:
        try:
            l = Lecture.query.filter_by(name=lect).one()
            lectures.append(l)
        except NoResultFound:
            # no dice, add a new lecture
            l = Lecture(name=lect, validated=validated)
            lectures.append(l)
            sqla.session.add(l)
    return lectures

def _match_examinants(examinant_names, validated):
    examinants = []
    for examinant in examinant_names:
        try:
            ex = Examinant.query.filter_by(name=examinant).one()
            examinants.append(ex)
        except NoResultFound:
            ex = Examinant(name=examinant, validated=validated)
            examinants.append(ex)
            sqla.session.add(ex)
    return examinants


def submit_documents(validated):
    """Student document submission endpoint

    POST data must be multipart, with the `json` part conforming to
    DocumentLoadSchema and the `file` part being a pdf file.

    Uploaded files are stored in subdirectories below config.DOCUMENT_DIRECTORY.

    This method may raise AssertionErrors when the user sends invalid data.
    """
    # we can't use @deserialize because this endpoint uses multipart form data
    data = json.loads(request.form['json'])
    if get_user():
        (data, errors) = FullDocumentLoadSchema().load(data)
        if (data.get('document_type') == 'written' and data.get('solution') not in ['official', 'inofficial', 'none']
                or data.get('document_type') != 'written' and data.get('solution') is not None):
            errors['solution'] = 'Invalid value.'
    else:
        (data, errors) = DocumentLoadSchema().load(data)
    if errors:
        raise ClientError(*errors)
    assert 'file' in request.files
    file = request.files['file']
    if not _allowed_file(file.filename):
        raise ClientError('file extension not allowed', status=406)
    lectures = _match_lectures(data['lectures'], validated)
    examinants = _match_examinants(data['examinants'], validated)
    date = data['date']
    if not get_user():
        assert date <= datetime.date.today()

    student_name = data.get('student_name')
    if student_name is None or student_name.isspace():
        student_name = None
    deposit_return_eligible = student_name is not None
    early_document_eligible = student_name is not None and any(lecture.early_document_eligible for lecture in lectures)

    new_doc = Document(
            department=data['department'],
            lectures=lectures,
            examinants=examinants,
            date=date,
            number_of_pages=0,  # will be filled in later or upon validation
            document_type=data['document_type'],
            validated=validated,
            validation_time=datetime.datetime.now() if validated else None,
            comment=data.get('comment'),
            solution=data.get('solution'),
            submitted_by=student_name,
            early_document_state=PaymentState.ELIGIBLE if early_document_eligible else PaymentState.NOT_ELIGIBLE,
            deposit_return_state=PaymentState.ELIGIBLE if deposit_return_eligible else PaymentState.NOT_ELIGIBLE
    )
    sqla.session.add(new_doc)

    # we have the db side of things taken care of, now save the file
    # and tell the db where to find the file
    sqla.session.flush()  # necessary for id field to be populated
    save_file(new_doc, file)
    if validated:
        # we don't trust other people's PDFs...
        new_doc.number_of_pages = number_of_pages(new_doc)
    sqla.session.commit()
    app.logger.info("New document submitted (id: {})".format(new_doc.id))
    if validated:
        config.document_validated(document_path(new_doc.id))
    return {'early_document_eligible': early_document_eligible}

# take heed when renaming this, it's referenced as string in the admin UI
@app.route('/api/view/<int:instance_id>')
@handle_client_errors
def view_document(instance_id):
    if get_user() or is_kiosk():
        doc = Document.query.get(instance_id)
        if doc is None or not doc.has_file:
            raise ClientError('document not found', status=404)
        return send_file(document_path(doc.id))
    else:
        return unauthorized()
