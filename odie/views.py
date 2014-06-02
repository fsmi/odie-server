import datetime
import json
import psycopg2
import psycopg2.extras

from django.http import HttpResponse
from django.views.decorators.http import require_GET, require_POST

import settings

class _JSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime.date):
            return obj.isoformat()
        return super(json.JSONEncoder, self).default(obj)

def _exec_prfproto(sql, **params):
    conn = psycopg2.connect(settings.PRFPROTO_DB)
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(sql, params)
    finally:
        conn.close()
    return HttpResponse(json.dumps(cur.fetchall(), cls=_JSONEncoder), content_type='application/json')

@require_GET
def lectures(request):
    return _exec_prfproto('''
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
                          ''')

@require_GET
def documents_of_lecture(request, lecture):
    return _exec_prfproto('''
SELECT 2 * id AS id, datum AS date, ARRAY[prof] AS examinants, ARRAY[vorlesung] AS lectures, kommentar AS comment, seiten AS pages, 'written' AS examType
FROM klausuren
WHERE datum > '1981-01-01' AND veraltet = FALSE AND vorlesung = %(lecture)s
UNION
SELECT 2 * protokolle.id + 1 AS id, datum AS date, (
    SELECT array_agg(pruefername)
    FROM pruefungpruefer
    JOIN pruefer ON prueferid = pruefer.id
    WHERE protokollid = protokolle.id
    GROUP BY protokolle.id
) AS examinants, (
    SELECT array_agg(vorlesung)
    FROM pruefungvorlesung
    JOIN vorlesungen ON vorlesungsid = vorlesungen.id
    WHERE protokollid = protokolle.id
    GROUP BY protokolle.id
) AS lectures, '' AS comment, seiten AS pages, 'oral' AS examType
FROM protokolle
JOIN pruefungvorlesung ON protokollid = protokolle.id
JOIN vorlesungen ON vorlesungsid = vorlesungen.id
WHERE vorlesung = %(lecture)s
                          ''', lecture=lecture)
