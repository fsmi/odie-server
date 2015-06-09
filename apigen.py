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


def endpoint(url, model, schemas={}, auth_methods=[], additional_methods=[], callback=lambda *_1, **_2: None):
    """Creates an API endpoint

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

    @login_required_for_methods(auth_methods)
    def route(instance_id=None):
        if request.method == 'DELETE':
            obj = model.query.get(instance_id)
            db.session.delete(obj)
            callback(obj)
            db.session.commit()
            return {}
        if request.method == 'POST':
            assert 'POST' in schemas, "POST schema missing"
            try:
                (obj, errors) = schemas['POST']().load(request.get_json(force=True))
                if errors:
                    raise ClientError(*errors)
                if model:
                    db.session.add(obj)
                callback(obj)
                db.session.commit()
                return {}
            except (ValueError, ValidationError):
                raise ClientError("failed to parse json")
        if request.method == 'GET' and instance_id is None:  # GET MANY
            assert 'GET' in schemas, "GET schema missing"
            schema = schemas['GET']
            q = json.loads(request.args.get('q', '{}'))
            query = jsonquery(db.session, model, q) if q else model.query
            result = query.all()
            obj =  serialize(result, schema, many=True)
            callback(obj)
            return obj
        if request.method == 'GET'and instance_id is not None:  # GET SINGLE
            result = model.query.get(instance_id)
            obj = serialize(result, schema)
            callback(obj)
            return obj
        raise NotImplementedError

    # flask requires route names and routed urls to be unique. We can use that here.
    methods = list(schemas.keys()) + additional_methods
    route.__name__ = ':'.join(methods) + url
    app.route(url, methods=methods)(route)


