#! /usr/bin/env python3

import json

from odie import app, db, ClientError
from serialization_schemas import serialize

from functools import wraps
from flask import request
from flask.ext.login import login_required
from jsonquery import jsonquery
from marshmallow import ValidationError


# Flask-login's @login_required decorator only supports all-or-nothing authentication,
# however the orders API is only restricted for GET requests, hence this

def login_required_for_methods(methods):
    def _decorator(f):
        login_f = login_required(f)
        @wraps(f)
        def wrapped_f(*args, **kw):
            if request.method in methods:
                return login_f(*args, **kw)
            return f(*args, **kw)
        return wrapped_f

    return _decorator


def accepts_json(schema):
    def _decorator(f):
        @wraps(f)
        def wrapped_f(*args, **kwargs):
            (obj, errors) = schema().load(request.get_json(force=True))
            if errors:
                raise ClientError(*errors)
            return f(*args, data=obj, **kwargs)
        return wrapped_f
    return _decorator



ROUTE_ID = 0


def endpoint(model, schemas={}, methods=[], callback=lambda *_1, **_2: None):
    """Creates and returns an API endpoint handler

    Can create both SINGLE-style and MANY-style endpoints. The generated route simply
    differentiates between the two cases through the presence/absence of an instance_id
    parameter in the url.

    schemas: dictionary of serializers/deserializers.
            These keys also define permissible methods.
    model: The db.Model to query. Mustn't be None for GET-enabled endpoints
    additional_methods: additional methods to register. Useful in the case of DELETE,
            which obviously doesn't need a serializer.
    callback: callback to call before committing. The object relevant to the request
            is given as parameter (e.g. the deserialized object POSTed)
            Note: the session is not committed after GET requests, so the callback
            will have to handle that as needed.
    """
    methods = list(schemas.keys()) + methods
    def handle_get(instance_id=None):
        if instance_id is None:  # GET MANY
            assert 'GET' in schemas, "GET schema missing"
            schema = schemas['GET']
            q = json.loads(request.args.get('q', '{}'))
            query = jsonquery(db.session, model, q) if q else model.query
            result = query.all()
            obj = serialize(result, schema, many=True)
            callback(obj)
            return obj
        else:  # GET SINGLE
            result = model.query.get(instance_id)
            obj = serialize(result, schema)
            callback(obj)
            return obj

    def handle_delete(instance_id):
        obj = model.query.get(instance_id)
        db.session.delete(obj)
        callback(obj)
        db.session.commit()
        return {}

    @accepts_json(schemas['POST'] if 'POST' in schemas else None)
    def handle_post(data=None):
        if model:
            db.session.add(data)
        callback(data)
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


