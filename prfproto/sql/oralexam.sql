CREATE OR REPLACE VIEW documents AS
SELECT 2 * id AS id, datum AS date, ARRAY[prof] AS examinants, ARRAY[vorlesung] AS lectures, kommentar AS comment, seiten AS pages, 'written' AS "examType"
FROM klausuren
WHERE datum > '1981-01-01' AND veraltet = FALSE
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
) AS lectures, '' AS comment, seiten AS pages, 'oral' AS "examType"
FROM protokolle
JOIN pruefungvorlesung ON protokollid = protokolle.id
JOIN vorlesungen ON vorlesungsid = vorlesungen.id
ORDER BY date DESC;
