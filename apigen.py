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


def instance_endpoint(url, model, schema=None, methods=['GET'], auth_methods=[]):
    """Creates an endpoint for single instance requests (e.g. /api/endpoint/1)

    Currently only handles GET and DELETE requests.
    url must specify a single URL parameter which is an int called `instance_id`.
    """
    @login_required_for_methods(auth_methods)
    def route(instance_id):
        if request.method == 'GET':
            result = model.query.get(instance_id)
            return serialize(result, schema)
        if request.method == 'DELETE':
            obj = model.query.get(instance_id)
            db.session.delete(obj)
            db.session.commit()
            return {}
        raise NotImplementedError

    # flask requires route names and routed urls to be unique. We can use that here.
    route.__name__ = url
    app.route(url, methods=methods)(route)


def collection_endpoint(url, schemas, model, auth_methods=[]):
    """Creates an endpoint for collection requests (e.g. /api/endpoint)

    Currently only handles GET and POST requests.

    serdes: dictionary of serializers/deserializers.
            These keys also define permissible methods.
    model: The db.Model to query. Mustn't be None for GET-enabled endpoints
    """

    @login_required_for_methods(auth_methods)
    def route():
        if request.method == 'POST':
            assert 'POST' in schemas, "POST schema missing"
            try:
                (obj, errors) = schemas['POST']().load(request.get_json(force=True))
                if errors:
                    raise ClientError(*errors)
                else:
                    db.session.add(obj)
                    db.session.commit()
                    return {}
            except (ValueError, ValidationError):
                raise ClientError("failed to parse json")
        if request.method == 'GET':
            assert 'GET' in schemas, "GET schema missing"
            schema = schemas['GET']
            q = json.loads(request.args.get('q', '{}'))
            query = jsonquery(db.session, model, q) if q else model.query
            result = query.all()
            return serialize(result, schema, many=True)
        raise NotImplementedError

    # flask requires route names and routed urls to be unique. We can use that here.
    route.__name__ = url
    app.route(url, methods=schemas.keys())(route)


