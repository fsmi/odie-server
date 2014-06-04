CREATE TABLE klausuren (
    id bigint NOT NULL,
    vorlesung text,
    prof text,
    datum date,
    kommentar text,
    bestand integer DEFAULT 0,
    sollbestand integer DEFAULT 0,
    gueltigbis date,
    seiten integer,
    verkauft bigint DEFAULT 0,
    veraltet boolean DEFAULT false
);

INSERT INTO klausuren (id, vorlesung, prof, datum, kommentar, seiten) VALUES (1, 'Einführung in die Vorlesungsnamensgestaltung', 'Ahnels', '2001-01-01', 'mit Musterlösung', 101);
INSERT INTO klausuren (id, vorlesung, prof, datum, kommentar, seiten) VALUES (2, 'Einführung in die Vorlesungsnamensgestaltung', 'Ahnels', '2002-01-01', 'mit Musterlösung und Sternchen', 1001);
INSERT INTO klausuren (id, vorlesung, prof, datum, kommentar, seiten) VALUES (3, 'Einführung in die Vorlesungsnamensgestaltung', 'Bertsen', '2003-01-01', NULL, 10001);
INSERT INTO klausuren (id, vorlesung, prof, datum, kommentar, seiten) VALUES (3, 'Fortgeschrittene Adjektivattributierung', 'Certz', '2005-01-01', NULL, 3);

CREATE TABLE protokolle (
    id bigint NOT NULL,
    gebiet bigint NOT NULL,
    datum date NOT NULL,
    seiten bigint NOT NULL,
    ausgedruckt_fuer_ordner boolean DEFAULT false NOT NULL
);

INSERT INTO protokolle VALUES (1, 1, '1998-9-9', 2);
INSERT INTO protokolle VALUES (2, 1, '1999-9-9', 3);
INSERT INTO protokolle VALUES (3, 2, '1998-9-9', 4);
INSERT INTO protokolle VALUES (4, 2, '1999-9-9', 5);

CREATE TABLE pruefer (
    id bigint NOT NULL,
    pruefername text NOT NULL
);

INSERT INTO pruefer VALUES (1, 'Ahnels');
INSERT INTO pruefer VALUES (2, 'Certz');

CREATE TABLE pruefungpruefer (
    protokollid bigint NOT NULL,
    prueferid bigint NOT NULL
);

INSERT INTO pruefungpruefer VALUES (1, 1);
INSERT INTO pruefungpruefer VALUES (1, 2);
INSERT INTO pruefungpruefer VALUES (2, 1);
INSERT INTO pruefungpruefer VALUES (3, 2);
INSERT INTO pruefungpruefer VALUES (4, 2);

CREATE TABLE pruefungvorlesung (
    protokollid bigint NOT NULL,
    vorlesungsid bigint NOT NULL,
    dozent text,
    id bigint NOT NULL
);

INSERT INTO pruefungvorlesung VALUES (1, 1, 'Ahnels', 1);
INSERT INTO pruefungvorlesung VALUES (1, 2, 'Certz', 2);
INSERT INTO pruefungvorlesung VALUES (2, 2, 'Certz', 3);
INSERT INTO pruefungvorlesung VALUES (3, 1, 'Ahnels', 4);
INSERT INTO pruefungvorlesung VALUES (4, 2, 'Derzen', 5);

CREATE TABLE vorlesungen (
    id bigint NOT NULL,
    vorlesung text NOT NULL
);

INSERT INTO vorlesungen VALUES (1, 'Fortgeschrittene Adjektivattributierung');
INSERT INTO vorlesungen VALUES (2, 'Mensch-Toastbrot-Töaßter-Kommunikation');

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
ORDER BY date DESC
