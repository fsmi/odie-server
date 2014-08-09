import datetime
import json
import logging
import urllib

from django.db import connections
from django.http import HttpResponse, HttpResponseForbidden, HttpResponseBadRequest
from django.views.decorators.http import require_GET, require_POST, require_http_methods
from django.contrib import auth

from odie import models, settings
import prfproto.models

# returns 403 instead of login_required's redirect
def _login_required(view):
    def decorator(request, *params):
        if request.user.is_authenticated():
            return view(request, *params)
        else:
            return HttpResponseForbidden('Not logged in')
    return decorator

class _JSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime.date):
            return obj.isoformat()
        return json.JSONEncoder.default(self, obj)

def _JSONResponse(obj):
    return HttpResponse(json.dumps(obj, cls=_JSONEncoder), content_type='application/json')

def _exec_prfproto(sql, **params):
    # from https://docs.djangoproject.com/en/1.6/topics/db/sql/#executing-custom-sql-directly
    def dictfetchall(cursor):
        "Returns all rows from a cursor as a dict"
        desc = cursor.description
        return [dict(zip([col[0] for col in desc], row))
                for row in cursor.fetchall()]

    cur = connections['prfproto'].cursor()
    cur.execute(sql, params)
    return dictfetchall(cur)

@require_GET
def lectures(request):
    return _JSONResponse(_exec_prfproto('''
SELECT vorlesung AS name, COUNT(*) AS document_count
FROM (
  SELECT vorlesung, id
  FROM klausuren
  WHERE datum > '1981-01-01' AND veraltet = FALSE
 UNION ALL
  SELECT vorlesung, vorlesungsid
  FROM pruefungvorlesung
  JOIN vorlesungen ON vorlesungsid = vorlesungen.id
) AS lectures
GROUP BY name
ORDER BY name
                          '''))

@require_GET
def documents_of_lecture(request, lecture):
    return _JSONResponse(_exec_prfproto('SELECT * FROM documents WHERE %(lecture)s = ANY(lectures)', lecture=urllib.unquote(lecture)))

def _decode_json_body(request):
    if request.META['CONTENT_TYPE'] != 'application/json; charset=UTF-8':
        raise Exception('Not a JSON request: ' + request.META['CONTENT_TYPE'])

    return json.loads(str.decode(request.body, 'utf-8'))

@require_http_methods(['POST', 'DELETE'])
def modify_cart(request, name):
    if request.method == 'POST':
        return create_cart(request, name)
    if request.method == 'DELETE':
        return delete_cart(request, int(name))

def create_cart(request, name):
    cart = models.Cart()
    cart.name = urllib.unquote(name)
    cart.save()  # populate cart.id
    cart.cartdocument_set = [models.CartDocument(cart=cart, document_id=document_id)
                             for document_id in _decode_json_body(request)]
    return HttpResponse()

@_login_required
def delete_cart(request, cart_id):
    models.Cart.objects.get(id=cart_id).delete()
    return HttpResponse()

@require_GET
@_login_required
def carts(request):
    carts = models.Cart.objects.all().prefetch_related('cartdocument_set')
    documents = _exec_prfproto('SELECT * FROM documents WHERE id IN ({})'.format(','.join({str(document_id)
                                                                                           for cart in carts
                                                                                           for document_id in cart.document_ids})))
    return _JSONResponse([{
        'id': cart.id,
        'creationTime': cart.creation_time,
        'name': cart.name,
        'documents': [doc for doc in documents if doc['id'] in cart.document_ids]
    } for cart in carts])

@require_POST
def login(request):
    credentials = _decode_json_body(request)
    user = auth.authenticate(username=credentials['user'], password=credentials['password'])
    if user:
        auth.login(request, user)
        return HttpResponse()
    else:
        return HttpResponseForbidden('Wrong credentials')

@_login_required
@require_GET
def user(request):
    return _JSONResponse({
        'user': request.user.username,
        'firstName': request.user.first_name,
        'lastName': request.user.last_name,
    })

@_login_required
@require_POST
def logout(request):
    auth.logout(request)
    return HttpResponse()

@_login_required
@require_POST
def log_erroneous_copies(request):
    cents = int(_decode_json_body(request)['cents'])
    if cents <= 0:
        return HttpResponseBadRequest('non-positive correction amount')

    prfproto.models.AccountingLog(account_id=2222,
                                  amount=-cents / 100.0,
                                  description='Fehlkopien',
                                  by_uid=request.user.unix_uid).save()
    return HttpResponse()

@_login_required
@require_POST
def print_job(request):
    job = _decode_json_body(request)
    exams = map(prfproto.models.Exam.get, job['documents'])
    if not exams:
        return HttpResponseBadRequest('empty print job')

    deposit_count = job['depositCount']
    assert type(deposit_count) is int and deposit_count >= 0
    price = sum(exam.price for exam in exams)
    logging.debug('price %s, deposit %s', price, deposit_count * settings.DEPOSIT_AMOUNT)
    # round up to next 10 cents
    price = 10 * (price/10 + (1 if price % 10 else 0))

    settings.do_print(['external', request.user.username, job['coverText'], ''] + [exam.file_path for exam in exams])
    for _ in range(deposit_count):
        prfproto.models.ProtocolDeposit(student_name=job['coverText'],
                                        amount=settings.DEPOSIT_AMOUNT / 100.0,
                                        by_user=request.user.get_full_name()).save()
        prfproto.models.AccountingLog(account_id=0,
                                      amount=settings.DEPOSIT_AMOUNT / 100.0,
                                      description='Protokollpfand',
                                      by_uid=request.user.unix_uid).save()

    prfproto.models.AccountingLog(account_id=2222,
                                  amount=price / 100.0,
                                  description='Klausur-/Protokolldruck',
                                  by_uid=request.user.unix_uid).save()
    return HttpResponse()
