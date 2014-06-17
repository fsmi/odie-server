import datetime
import json
import os

from django.db import connections
from django.http import HttpResponse, HttpResponseForbidden, HttpResponseBadRequest
from django.views.decorators.http import require_GET, require_POST
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
        return super(json.JSONEncoder, self).default(obj)

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
    return _JSONResponse(_exec_prfproto('SELECT * FROM documents WHERE %(lecture)s = ANY(lectures)', lecture=lecture))

def _decode_json_body(request):
    if request.META['CONTENT_TYPE'] != 'application/json; charset=UTF-8':
        raise Exception('Not a JSON request: ' + request.META['CONTENT_TYPE'])

    return json.loads(str.decode(request.body, 'utf-8'))

@require_POST
def create_cart(request, name):
    cart = models.Cart()
    cart.name = name
    cart.date = datetime.datetime.now()
    cart.save()  # populate cart.id
    cart.cartdocument_set = [models.CartDocument(cart=cart, document_id=document_id)
                             for document_id in _decode_json_body(request)]
    return HttpResponse()

@_login_required
@require_GET
def carts(request):
    carts = models.Cart.objects.all().prefetch_related('cartdocument_set')
    documents = _exec_prfproto('SELECT * FROM documents WHERE id IN ({})'.format(','.join({str(document_id)
                                                                                           for cart in carts
                                                                                           for document_id in cart.document_ids})))
    return _JSONResponse([{
        'id': cart.id,
        'date': cart.date,
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
@require_POST
def print_job(request):
    job = _decode_json_body(request)
    exams = map(prfproto.models.Exam.get, job['documents'])
    if not exams:
        return HttpResponseBadRequest('empty print job')

    settings.do_print(['external', job['coverText'], ''] + [exam.file_path for exam in exams])
    deposit_count = job['depositCount']
    deposit = deposit_count * settings.DEPOSIT_AMOUNT
    price = sum(exam.price for exam in exams)

    if deposit_count:
        prfproto.models.ProtocolDeposit(student_name=job['coverText'],
                                        amount=deposit,
                                        by_user=request.user.get_full_name()).save()
        prfproto.models.AccountingLog(account_id=0,
                                      amount=deposit,
                                      description='Protokollpfand',
                                      by_uid=request.user.unix_uid).save()

    prfproto.models.AccountingLog(account_id=2222,
                                  amount=price,
                                  description='Klausur-/Protokolldruck',
                                  by_uid=request.user.unix_uid).save()
    return HttpResponse()
