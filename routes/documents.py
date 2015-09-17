#! /usr/bin/env python3

import barcode
import config
import datetime
import json
import os

from flask import request, send_file, Response
from flask.ext.login import current_user, login_required
from marshmallow import Schema, fields
from marshmallow.validate import OneOf
from sqlalchemy.orm import subqueryload
from sqlalchemy.orm.exc import NoResultFound

from .common import IdSchema, DocumentDumpSchema
from odie import app, sqla, csrf, ClientError
from api_utils import endpoint, api_route, handle_client_errors, document_path, save_file, serialize
from db.documents import Lecture, Document, Examinant


## Barcode scanner support is achieved using long-lived HTTP(S) connections and
## server-sent events (https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events)

def scanner_stream(location, id, username):
    assert location in config.FS_CONFIG['OFFICES']
    assert 0 <= id <= len(config.LASER_SCANNERS[location])
    (host, port) = config.LASER_SCANNERS[location][id]
    bs = barcode.BarcodeScanner(host, port, username)
    for doc in bs:
        if doc is None:
            # socket read has timeoutet, try to write to output stream
            # If run locally, yielding the empty string would suffice, but wsgi doesn't
            # attempt to write to the socket in that case, so we do this instead
            yield '\n'
        else:
            yield 'data: ' + json.dumps(serialize(doc, DocumentDumpSchema)) + '\n\n'


@app.route('/api/scanner/<location>/<int:id>')
@login_required
def scanner(location, id):
    return Response(scanner_stream(location, id, current_user.first_name), mimetype='text/event-stream', headers={'X-Accel-Buffering': 'no'})


class LectureDumpSchema(IdSchema):
    name = fields.Str()
    aliases = fields.List(fields.Str())
    comment = fields.Str()
    validated = fields.Boolean()

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


class DocumentLoadSchema(Schema):  # used by student document submission
    department = fields.Str(required=True, validate=OneOf(['computer science', 'mathematics', 'other']))
    lectures = fields.List(fields.Str(), required=True)
    examinants = fields.List(fields.Str(), required=True)
    date = fields.Date(required=True)
    document_type = fields.Str(required=True, validate=OneOf(['oral', 'oral reexam']))
    student_name = fields.Str(required=True)


def _allowed_file(filename):
    return os.path.splitext(filename)[1] in config.SUBMISSION_ALLOWED_FILE_EXTENSIONS


@api_route('/api/documents', methods=['POST'])
@csrf.exempt
def submit_document():
    """Student document submission endpoint

    POST data must be multipart, with the `json` part conforming to
    DocumentLoadSchema and the `file` part being a pdf file.

    Uploaded files are stored in subdirectories below config.DOCUMENT_DIRECTORY.

    This method may raise AssertionErrors when the user sends invalid data.
    """
    # we can't use @deserialize because this endpoint uses multipart form data
    data = json.loads(request.form['json'])
    (data, errors) = DocumentLoadSchema().load(data)
    if errors:
        raise ClientError(*errors)
    assert 'file' in request.files
    file = request.files['file']
    if not _allowed_file(file.filename):
        raise ClientError('file extension not allowed', status=406)
    lectures = []
    for lect in data['lectures']:
        try:
            l = Lecture.query.filter_by(name=lect).one()
            lectures.append(l)
        except NoResultFound:
            # no dice, add a new unverified lecture
            l = Lecture(name=lect, validated=False)
            lectures.append(l)
            sqla.session.add(l)
    examinants = []
    for examinant in data['examinants']:
        try:
            ex = Examinant.query.filter_by(name=examinant).one()
            examinants.append(ex)
        except NoResultFound:
            ex = Examinant(name=examinant, validated=False)
            examinants.append(ex)
            sqla.session.add(ex)
    date = data['date']
    assert date <= datetime.date.today()
    new_doc = Document(
            department=data['department'],
            lectures=lectures,
            examinants=examinants,
            date=date,
            number_of_pages=0,  # this will be filled in upon validation
            document_type=data['document_type'],
            validated=False,
            submitted_by=data['student_name'])
    sqla.session.add(new_doc)

    # we have the db side of things taken care of, now save the file
    # and tell the db where to find the file
    sqla.session.flush()  # necessary for id field to be populated
    save_file(new_doc, file)
    sqla.session.commit()
    app.logger.info("New document submitted (id: {})".format(new_doc.id))
    return {}

# take heed when renaming this, it's referenced as string in the admin UI
@app.route('/api/view/<int:instance_id>')
@handle_client_errors
@login_required
def view_document(instance_id):
    doc = Document.query.get(instance_id)
    if doc is None or not doc.has_file:
        raise ClientError('document not found', status=404)
    return send_file(document_path(doc.id))
