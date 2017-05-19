SET search_path = documents;


ALTER TABLE documents.documents ADD COLUMN early_document_eligible BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE documents.documents ADD COLUMN deposit_return_eligible BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE documents.documents ADD COLUMN has_barcode BOOLEAN NOT NULL DEFAULT FALSE;


CREATE OR REPLACE FUNCTION lectures_early_document_reward_until(lec_id int, early_document_count int, grace_period_days int) RETURNS timestamptz AS $$
DECLARE
	result timestamptz;
BEGIN
	LOCK TABLE documents.lectures, documents.documents, documents.lecture_docs IN SHARE MODE;
	IF NOT exists(select 1 from documents.lectures where id=lec_id) THEN
		RAISE EXCEPTION 'Lecture % does not exist', lec_id;
	END IF;
	IF early_document_count < 0 THEN
		RAISE EXCEPTION 'early_document_count must be positive or zero';
	END IF;
	IF grace_period_days < 0 THEN
		RAISE EXCEPTION 'grace_period_days must be positive or zero';
	END IF;
	IF early_document_count = 0 THEN
		return null;
	END IF;

	select doc.validation_time into result
	from documents.documents as doc
	join documents.lecture_docs as jt on jt.document_id = doc.id
	join documents.lectures as lec on jt.lecture_id = lec.id
	where doc.validation_time is not null
	and lec.id = lec_id
	and doc.validated = true
	--and lec.validated = true
	order by doc.validation_time ASC
	limit 1 offset (early_document_count-1);
	IF NOT FOUND THEN
		return null;
	END IF;

	return result + interval '1' day * grace_period_days;
END
$$ LANGUAGE plpgsql SECURITY DEFINER SET search_path = documents, pg_temp;
ALTER FUNCTION lectures_early_document_reward_until(int, int, int) OWNER TO garfield_operations;
REVOKE ALL ON FUNCTION lectures_early_document_reward_until(int, int, int) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION lectures_early_document_reward_until(int, int, int) TO garfield_web;


UPDATE documents.documents SET deposit_return_eligible = true WHERE submitted_by IS NOT NULL;
UPDATE documents.documents SET has_barcode = true WHERE validation_time IS NOT NULL;
UPDATE documents.documents SET validation_time = null where validated = false or validated IS NULL;
update documents.documents set early_document_eligible = true
where submitted_by is not null and id in
(
	select distinct out_of_identifiers.document_id from documents.lecture_docs as out_of_identifiers 
	join
	(
		select parent.id as id,
		(
			select doc.validation_time + interval '14' day
			from documents.documents as doc
			join documents.lecture_docs as jt on jt.document_id = doc.id
			--join documents.lectures as lec on jt.lecture_id = lec.id
			where doc.validation_time is not null
			and jt.lecture_id = parent.id
			and doc.validated = true
			--and lec.validated = true
			order by doc.validation_time ASC
			limit 1 offset 4
		) as until 
		from documents.lectures as parent
	) as sq1
	on out_of_identifiers.lecture_id = sq1.id
	where sq1.until is null
	or sq1.until > now()
);

