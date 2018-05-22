#! /usr/bin/env python3

import config

from flask import session, make_response, request
from marshmallow import fields, post_load, Schema
from marshmallow.validate import Length
from sqlalchemy.orm import subqueryload

from .common import IdSchema, DocumentDumpSchema
from odie import app, csrf, ClientError, sqla
from login import get_user, is_kiosk, login_required
from api_utils import endpoint, api_route, handle_client_errors, serialize
from db.documents import Deposit
from db.odie import Order
from db.userHash import userHash, ToManyAttempts
import json

## Routes may either return something which can be turned into json using
## flask.jsonify or a api_utils.PaginatedResult. The actual response is assembled
## in api_utils.api_route.

@api_route('/api/config')
def get_config():
    return dict(config.FS_CONFIG, IS_KIOSK=is_kiosk())

@app.route('/kiosk')
@handle_client_errors
@login_required
def kiosk_handover():
    # if you find yourself in kiosk mode unable to escape... delete the cookie.
    session['is_kiosk'] = True
    # We don't want the kiosk user to still be logged in
    response = make_response('Kiosk Mode enabled.')
    response.set_cookie(config.AUTH_COOKIE, value='', expires=0)
    return response

class UserDumpSchema(Schema):
    username = fields.Str()
    first_name = fields.Str()
    last_name = fields.Str()
    office = fields.Function(config.try_get_office)


class LoginDumpSchema(Schema):
    user = fields.Nested(UserDumpSchema)
    token = fields.Str()

# exempting this from CSRF is okay since the dangers of CSRF only apply to endpoints that do something
# whereas this simply returns some data. As long as CORS is set up correctly, we're fine

@api_route('/api/user_info')
@csrf.exempt
@login_required
def user_info():
    # Explicitly pass the csrf token cookie value for cross-origin clients.
    return serialize({'user': get_user(), 'token': csrf._get_token()}, LoginDumpSchema)


class OrderDumpSchema(IdSchema):
    name = fields.Str()
    documents = fields.List(fields.Nested(DocumentDumpSchema))
    creation_time = fields.Date()


api_route('/api/orders', methods=['GET'])(
login_required(
endpoint(
        schemas={
            'GET': OrderDumpSchema,
        },
        query_fn=lambda: Order.query.options(subqueryload('items.document.lectures'), subqueryload('items.document.examinants')))
))


class OrderLoadSchema(Schema):
    name = fields.Str(required=True, validate=Length(min=1))
    document_ids = fields.List(fields.Int(), required=True)

  #  @post_load
  # def make_order(self, data):
  #      try:
  #          uh = userHash()
  #          rand = uh.returnIdCard()
  #          session['placed_orders'] = rand
  #          return Order(name=rand, document_ids=data['document_ids'])
  #      except KeyError:
  #          return None
  #      except ToManyAttempts:
  #          return None


@app.route("/api/orders", methods=["POST"])
@csrf.exempt
def submit_orders():
    try:
        uh = userHash()
        rand = uh.returnIdCard()
        data = OrderLoadSchema().loads(request.data)
        order = Order(name=rand, document_ids=data['document_ids'])
        sqla.session.add(order)
        sqla.session.commit()
        return '{"id":' + json.dumps(rand) + '}'
    except ToManyAttempts:
        ClientError('to many attempts to generate an id, please send a mail to odie@fsmi.uka.de', status=500)
    except KeyError:
        ClientError('error received, please send a mail to odie@fsmi.uka.de', status=500)


#api_route('/api/orders', methods=['POST'])(
#csrf.exempt(
#endpoint(
#        schemas={
#            'POST': OrderLoadSchema,
#        },
#        query_fn=None)
#))

api_route('/api/orders/<int:instance_id>', methods=['DELETE'])(
login_required(
endpoint(
        query_fn=lambda: Order.query,
        allow_delete=True)
))


class DepositDumpSchema(IdSchema):
    price = fields.Int()
    name = fields.Str()
    date = fields.Date()
    lectures = fields.List(fields.Str())


api_route('/api/deposits')(
login_required(
endpoint(
        schemas={'GET': DepositDumpSchema},
        query_fn=lambda: Deposit.query.options(subqueryload('lectures')))
))


