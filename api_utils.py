#! /usr/bin/env python3

import config
import json
import math

from odie import app, db, ClientError
from serialization_schemas import serialize

from functools import wraps
from flask import Flask, jsonify, request
from flask.ext.login import login_required
from jsonquery import jsonquery
from marshmallow import ValidationError
from sqlalchemy import inspect


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
            (obj, errors) = schema().load(request.get_json(force=True))
            if errors:
                raise ClientError(*errors)
            return f(*args, data=obj, **kwargs)
        return wrapped_f
    return _decorator


def filtered_results(query, schema, paginate=True):
    q = json.loads(request.args.get('q', '{}'))
    query = jsonquery(query, q) if q else query
    if not paginate:
        return serialize(query.all(), schema, many=True)
    page = int(request.args.get('page', '1'))
    items_per_page = config.ITEMS_PER_PAGE
    pag = query.paginate(page, items_per_page)
    return PaginatedResult(pag, schema)


# uniform response formatting:
# {"data": <jsonified route result>}
# or {"errors": <errors>} on ClientError
def api_route(url, *args, **kwargs):
    def decorator(f):
        @wraps(f)
        def wrapped_f(*f_args, **f_kwargs):
            try:
                data = f(*f_args, **f_kwargs)
                # automatically add 'page' attribute to returned object
                if isinstance(data, PaginatedResult):
                    result = data
                    data = result.data
                    return jsonify(data=result.data,
                            page=result.pagination.page,
                            number_of_pages=result.pagination.pages)
                return jsonify(data=data)
            except ClientError as e:
                return (jsonify(errors=e.errors), e.status, [])
        return Flask.route(app, url, *args, **kwargs)(wrapped_f)
    return decorator

ROUTE_ID = 0


def endpoint(query, schemas={}, allow_delete=False, paginate_many=True):
    """Creates and returns an API endpoint handler

    Can create both SINGLE-style and MANY-style endpoints. The generated route simply
    differentiates between the two cases through the presence/absence of an instance_id
    parameter in the url.

    Returns the handler, you have to register it with Flask yourself.

    schemas: dictionary of {<method>: serializer/deserializer}.
            These keys also define permissible methods.
    query: The query to operate on. Mustn't be None for GET-enabled endpoints
    paginate_many: whether to return paginated results (default:True)
            The 'page' GET-parameter selects the page
    """
    methods = list(schemas.keys())
    if allow_delete:
        methods.append('DELETE')

    def handle_get(instance_id=None):
        if instance_id is None:  # GET MANY
            assert 'GET' in schemas, "GET schema missing"
            schema = schemas['GET']
            return filtered_results(query, schema, paginate_many)
        else:  # GET SINGLE
            result = query.get(instance_id)
            obj = serialize(result, schema)
            return obj

    def handle_delete(instance_id):
        obj = query.get(instance_id)
        # since we don't know where this query came from, we need to detach obj
        # from its session before we can delete it. expunge does exactly this.
        inspect(obj).session.expunge(obj)
        db.session.delete(obj)
        db.session.commit()
        return {}

    @deserialize(schemas['POST'] if 'POST' in schemas else None)
    def handle_post(data=None):
        db.session.add(data)
        db.session.commit()
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


