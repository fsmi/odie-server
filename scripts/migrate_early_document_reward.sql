SET ROLE odie;
SET search_path = documents;


ALTER TABLE lecture_docs ADD PRIMARY KEY (lecture_id,document_id);
ALTER TABLE folder_lectures ADD PRIMARY KEY (folder_id,lecture_id);

ALTER TABLE documents ADD COLUMN early_document_eligible BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE documents ADD COLUMN deposit_return_eligible BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE documents ADD COLUMN has_barcode BOOLEAN NOT NULL DEFAULT FALSE;


CREATE OR REPLACE FUNCTION documents.lectures_early_document_reward_until(lec_id int, early_document_count int, grace_period_days int) RETURNS timestamptz AS $$
DECLARE
	result timestamptz;
BEGIN
	LOCK TABLE documents.lectures, documents.documents, documents.lecture_docs IN SHARE MODE;
	IF NOT exists(SELECT 1 FROM documents.lectures WHERE id=lec_id) THEN
		RAISE EXCEPTION 'Lecture % does not exist', lec_id;
	END IF;
	IF early_document_count <= 0 THEN
		RAISE EXCEPTION 'early_document_count must be positive';
	END IF;
	IF grace_period_days < 0 THEN
		RAISE EXCEPTION 'grace_period_days must be positive or zero';
	END IF;

	SELECT doc.validation_time into result
	FROM documents.documents AS doc
	JOIN documents.lecture_docs AS jt ON jt.document_id = doc.id
	JOIN documents.lectures AS lec ON jt.lecture_id = lec.id
	WHERE doc.validation_time IS NOT NULL
	AND doc.document_type = 'oral'
	AND lec.id = lec_id
	--and lec.validated = true
	ORDER BY doc.validation_time ASC
	LIMIT 1 OFFSET (early_document_count-1);
	IF NOT FOUND THEN
		return null;
	END IF;

	return result + interval '1' day * grace_period_days;
END
$$ LANGUAGE plpgsql SECURITY DEFINER SET search_path = documents, pg_temp;
REVOKE ALL ON FUNCTION lectures_early_document_reward_until(int, int, int) FROM PUBLIC;
ALTER FUNCTION lectures_early_document_reward_until OWNER TO odie;


UPDATE documents SET deposit_return_eligible = true WHERE submitted_by IS NOT NULL;
UPDATE documents SET has_barcode = true WHERE validation_time IS NOT NULL;
UPDATE documents SET validation_time = null where validated = false OR validated IS NULL;
ALTER TABLE documents DROP COLUMN validated;
UPDATE documents SET early_document_eligible = false;
-- UPDATE documents SET early_document_eligible = true
-- WHERE submitted_by IS NOT NULL AND document_type = 'oral' AND id IN
-- (
-- 	SELECT DISTINCT out_of_identifiers.document_id FROM lecture_docs AS out_of_identifiers
-- 	JOIN
-- 	(
-- 		SELECT lectures.id AS id, lectures_early_document_reward_until(lectures.id, 5, 14) AS until
-- 		FROM lectures
-- 	) AS sq1
-- 	ON out_of_identifiers.lecture_id = sq1.id
-- 	WHERE sq1.until IS NULL OR sq1.until > now()
-- );
