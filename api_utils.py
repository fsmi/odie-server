#! /usr/bin/env python3

import config
import os
import json
import datetime
import marshmallow
import traceback

from odie import app, sqla, ClientError
from login import get_user

from functools import wraps
from flask import Flask, Response, request
from jsonquery import jsonquery
from marshmallow import Schema, fields
from sqlalchemy import inspect
from PyPDF2 import PdfFileReader
from PyPDF2.utils import PdfReadError
from pytz import reference

def end_of_local_date(d):
    return datetime.datetime.combine(d, datetime.time(23, 59, 59, 999999, tzinfo=reference.LocalTimezone()))

def document_path(id):
    dir = os.path.join(config.DOCUMENT_DIRECTORY, str(id % 100))
    if not os.path.isdir(dir):
        os.makedirs(dir)
    return os.path.join(dir, str(id) + '.pdf')


def number_of_pages(document):
    try:
        with open(document_path(document.id), 'rb') as pdf:
            return PdfFileReader(pdf).getNumPages()
    except (PdfReadError, FileNotFoundError):
        # this is still user-provided data after all
        return 0


def save_file(document, file_storage):
    file_storage.save(document_path(document.id))
    file_storage.close()
    document.has_file = True
    document.number_of_pages = number_of_pages(document)


def serialize(data, schema, many=False):
    try:
        return schema().dump(data, many=many)
    except marshmallow.exceptions.ValidationError as e:
        raise ClientError(str(e), status=400)

class PaginatedResult(object):
    """Wraps results with pagination metadata"""

    def __init__(self, pagination, schema):
        self.pagination = pagination
        self.schema = schema

    @property
    def data(self):
        return serialize(self.pagination.items, self.schema, many=True)


def deserialize(schema):
    def _decorator(f):
        @wraps(f)
        def wrapped_f(*args, **kwargs):
            try:
                obj = schema().load(request.get_json(force=True))
            except marshmallow.exceptions.ValidationError as e:
                raise ClientError(str(e), status=500)
            return f(*args, data=obj, **kwargs)
        return wrapped_f
    return _decorator


class PaginatedResultSchema(Schema):
    data = fields.Raw()
    page = fields.Int(attribute='pagination.page')
    number_of_pages = fields.Int(attribute='pagination.pages')
    total = fields.Int(attribute='pagination.total')


# `allow_insecure` is *insecure* -- see comment in endpoint() regarding the `allow_insecure_authenticated`
# parameter. Note that in this function, `allow_insecure` does also apply to anonymous users.
def filtered_results(query, schema, paginate=True, allow_insecure=False):
    q = json.loads(request.args.get('q', '{}'))
    if allow_insecure:
        query = jsonquery(query, q) if q else query
    # ensure deterministic ordering
    # (we need this for paginated results with queries involving subqueries)
    # We assume that all queriable tables have an 'id' column
    query = query.order_by('id')
    if not paginate:
        return serialize(query.all(), schema, many=True)
    page = q.get('page', 1)
    items_per_page = config.ITEMS_PER_PAGE
    pag = query.paginate(page, items_per_page)
    return PaginatedResult(pag, schema)


def jsonify(*args, **kwargs):
    # http://flask.pocoo.org/snippets/45/
    def request_wants_json():
        best = request.accept_mimetypes \
            .best_match(['application/json', 'text/html'])
        return best == 'application/json' and \
            request.accept_mimetypes[best] > \
            request.accept_mimetypes['text/html']

    data = json.dumps(dict(*args, **kwargs))
    if not get_user() or request_wants_json():
        return Response(data, mimetype='application/json')
    else:
        # provide some HTML for flask-debugtoolbar to inject into
        return '<html><body><pre>{}</pre></body></html>'.format(data)

def handle_client_errors(f):
    @wraps(f)
    def wrapped_f(*f_args, **f_kwargs):
        try:
            return f(*f_args, **f_kwargs)
        except ClientError as e:
            return (jsonify(errors=e.errors), e.status, [])
    return wrapped_f


# uniform response formatting:
# {"data": <jsonified route result>}
# or {"errors": <errors>} on ClientError
def api_route(url, *args, **kwargs):
    def decorator(f):
        @wraps(f)
        @handle_client_errors
        def wrapped_f(*f_args, **f_kwargs):
            data = f(*f_args, **f_kwargs)
            if isinstance(data, PaginatedResult):
                return jsonify(serialize(data, PaginatedResultSchema))
            return jsonify(data=data)
        return Flask.route(app, url, *args, **kwargs)(wrapped_f)
    return decorator

ROUTE_ID = 0


def endpoint(query_fn, schemas=None, allow_delete=False, paginate_many=True, allow_insecure_authenticated=False):
    """Creates and returns an API endpoint handler

    Can create both SINGLE-style and MANY-style endpoints. The generated route simply
    differentiates between the two cases through the presence/absence of an instance_id
    parameter in the url.

    Returns the handler, you have to register it with Flask yourself.

    schemas: dictionary of {<method>: serializer/deserializer}.
            These keys also define permissible methods.
    query_fn: A callable returning a Query object. Mustn't be None for GET-enabled endpoints.
    paginate_many: whether to return paginated results (default:True)
            The 'page' GET-parameter selects the page
    allow_insecure_authenticated: If true, the 'q' parameter (JSON) will be parsed into an SQLAlchemy Query using the
                                  jsonquery library if the user is logged in. If the user is not logged in, this feature
                                  will stay disabled.
                                  As the name implies, this is insecure as it allows near-arbitrary user-controlled
                                  WHERE clauses in SELECT queries. This feature should be avoided as much as possible
                                  and only still exists for legacy compatibility reasons.
                                  It allows for non-obvious data leaks even when restricting the selected columns;
                                  see https://github.com/fsmi/odie-server/pull/168 for details.
    """
    if schemas is None:
        schemas = {}
    methods = list(schemas.keys())
    if allow_delete:
        methods.append('DELETE')

    def handle_get(instance_id=None):
        if instance_id is None:  # GET MANY
            assert 'GET' in schemas, "GET schema missing"
            schema = schemas['GET']
            allow_insecure = allow_insecure_authenticated and get_user()
            return filtered_results(query_fn(), schema, paginate_many, allow_insecure=allow_insecure)
        else:  # GET SINGLE
            result = query_fn().get(instance_id)
            obj = serialize(result, schema)
            return obj

    def handle_delete(instance_id):
        obj = query_fn().get(instance_id)
        # since we don't know where this query came from, we need to detach obj
        # from its session before we can delete it. expunge does exactly this.
        inspect(obj).session.expunge(obj)
        sqla.session.delete(obj)
        sqla.session.commit()
        return {}

    @deserialize(schemas['POST'] if 'POST' in schemas else None)
    def handle_post(data=None):
        sqla.session.add(data)
        sqla.session.commit()
        return {}

    def handle_generic(instance_id=None):
        if request.method == 'POST' and 'POST' in methods:
            return handle_post()
        elif request.method == 'GET' and 'GET' in methods:
            return handle_get(instance_id)
        elif request.method == 'DELETE' and 'DELETE' in methods:
            return handle_delete(instance_id)
        raise NotImplementedError

    # we need to make sure that *whatever happens*, Flask still has unique route identifiers
    global ROUTE_ID
    handle_generic.__name__ = '__generated_' + str(ROUTE_ID)
    ROUTE_ID += 1
    return handle_generic


class NonConfidentialException(Exception):
    pass

def event_stream(f):
    """Implements Server-Sent Events (https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events)

    f is expected to return an iterator that returns (event, data) pairs.
    'event' can be a str or None. 'data' can be any JSON serializable object, or None as a 'keepalive' value.
    The first datum will not be returned; instead it marks the end of the code that must be executed in the
    application context.
    """
    @wraps(f)
    def wrapped(*args, **kwargs):
        def get_stream():
            stream = f(*args, **kwargs)
            try:
                # skip first datum
                try:
                    next(stream)
                finally:
                    yield None

                for (event, data) in stream:
                    if event is not None:
                        yield 'event: {}\n'.format(event)
                    if data is not None:
                        yield 'data: {}\n\n'.format(json.dumps(data))
                    else:
                        # If run locally, yielding the empty string would suffice, but wsgi doesn't
                        # attempt to write to the socket in that case, so we do this instead
                        yield '\n'
            except ClientError as e:
                yield 'event: stream-error\ndata: {}\n\n'.format('\n'.join(e.errors))
                app.logger.exception(e)
            except NonConfidentialException as e:
                yield 'event: stream-error\ndata: {}\n\n'.format(e)
                app.logger.exception(e)
            except Exception as e:
                yield 'event: stream-error\ndata: internal server error: ' + str(e) + '  traceback: ' + str(traceback.print_exc()) + '\n\n'
                app.logger.exception(e)
        stream = get_stream()
        next(stream)  # skip first datum
        return Response(stream, mimetype='text/event-stream', headers={'X-Accel-Buffering': 'no'})
    return wrapped
