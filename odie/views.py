import datetime
import json
import psycopg2
import psycopg2.extras

from django.http import HttpResponse, HttpResponseForbidden
from django.views.decorators.http import require_GET, require_POST
from django.contrib import auth

from odie import models, settings

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
    conn = psycopg2.connect(settings.PRFPROTO_DB)
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(sql, params)
        return cur.fetchall()
    finally:
        conn.close()

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
    cart.cartdocument_set = [models.CartDocument(cart=cart, document_id=int(document_id))
                             for document_id in _decode_json_body(request)]
    return HttpResponse()

@_login_required
@require_GET
def carts(request):
    carts = models.Cart.objects.all()
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
