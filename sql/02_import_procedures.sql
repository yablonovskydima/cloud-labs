-- Import procedures used by the Lambda.
--
-- Flow for one file (all in one transaction):
--   1. CALL prepare_<table>_stage()            -- creates a temporary staging table (all columns text)
--   2. COPY stage_<table> FROM STDIN           -- the Lambda streams the file from S3 into it
--   3. CALL merge_<table>(source_file, ...)    -- cleans the rows and upserts them into the main table
--
-- Duplicate protection in merge_*:
--   - duplicates inside the file are collapsed (DISTINCT ON the business key);
--   - rows that already exist with the same data are skipped;
--   - rows that exist with different data are updated (ON CONFLICT ... DO UPDATE ... WHERE IS DISTINCT FROM);
--   - only new keys are inserted.
-- OUT parameters return how many rows were in the file, inserted, updated and skipped.

-- ---------------------------------------------------------------------------
-- city_routes (CSV)
-- ---------------------------------------------------------------------------
CREATE OR REPLACE PROCEDURE prepare_city_routes_stage()
LANGUAGE plpgsql AS $$
BEGIN
    DROP TABLE IF EXISTS stage_city_routes;
    CREATE TEMP TABLE stage_city_routes (
        uid text, agency_id text, short_name text, full_name text, description text,
        type text, homepage text, colour text, text_colour text, sort_order text
    ) ON COMMIT DROP;
END;
$$;

CREATE OR REPLACE PROCEDURE merge_city_routes(
    p_source_file    text,
    OUT rows_in_file integer,
    OUT inserted     integer,
    OUT updated      integer,
    OUT skipped      integer
)
LANGUAGE plpgsql AS $$
BEGIN
    SELECT count(*) INTO rows_in_file FROM stage_city_routes;

    DROP TABLE IF EXISTS stage_city_routes_clean;
    CREATE TEMP TABLE stage_city_routes_clean ON COMMIT DROP AS
    SELECT DISTINCT ON (route_uid) *
    FROM (
        SELECT trim(uid)::int                      AS route_uid,
               trim(agency_id)                     AS agency_id,
               trim(short_name)                    AS short_name,
               trim(full_name)                     AS full_name,
               nullif(trim(description), '')       AS description,
               trim(type)::smallint                AS route_type,
               nullif(trim(homepage), '')          AS homepage,
               nullif(trim(colour), '')            AS colour,
               nullif(trim(text_colour), '')       AS text_colour,
               nullif(trim(sort_order), '')::int   AS sort_order
        FROM stage_city_routes
        WHERE nullif(trim(uid), '') IS NOT NULL
    ) s
    ORDER BY route_uid;

    WITH upsert AS (
        INSERT INTO city_routes AS t (route_uid, agency_id, short_name, full_name, description,
                                      route_type, homepage, colour, text_colour, sort_order, source_file)
        SELECT route_uid, agency_id, short_name, full_name, description,
               route_type, homepage, colour, text_colour, sort_order, p_source_file
        FROM stage_city_routes_clean
        ON CONFLICT (route_uid) DO UPDATE
            SET agency_id   = EXCLUDED.agency_id,
                short_name  = EXCLUDED.short_name,
                full_name   = EXCLUDED.full_name,
                description = EXCLUDED.description,
                route_type  = EXCLUDED.route_type,
                homepage    = EXCLUDED.homepage,
                colour      = EXCLUDED.colour,
                text_colour = EXCLUDED.text_colour,
                sort_order  = EXCLUDED.sort_order,
                source_file = EXCLUDED.source_file,
                imported_at = now()
            WHERE (t.agency_id, t.short_name, t.full_name, t.description, t.route_type,
                   t.homepage, t.colour, t.text_colour, t.sort_order)
                  IS DISTINCT FROM
                  (EXCLUDED.agency_id, EXCLUDED.short_name, EXCLUDED.full_name, EXCLUDED.description,
                   EXCLUDED.route_type, EXCLUDED.homepage, EXCLUDED.colour, EXCLUDED.text_colour,
                   EXCLUDED.sort_order)
        RETURNING (xmax = 0) AS is_insert
    )
    SELECT count(*) FILTER (WHERE is_insert), count(*) FILTER (WHERE NOT is_insert)
    INTO inserted, updated
    FROM upsert;

    skipped := rows_in_file - inserted - updated;
END;
$$;

-- ---------------------------------------------------------------------------
-- agri_enterprises (JSON, converted to rows by the Lambda before COPY)
-- ---------------------------------------------------------------------------
CREATE OR REPLACE PROCEDURE prepare_agri_enterprises_stage()
LANGUAGE plpgsql AS $$
BEGIN
    DROP TABLE IF EXISTS stage_agri_enterprises;
    CREATE TEMP TABLE stage_agri_enterprises (
        edrpou text, name text, address text, director text, kved text
    ) ON COMMIT DROP;
END;
$$;

CREATE OR REPLACE PROCEDURE merge_agri_enterprises(
    p_source_file    text,
    OUT rows_in_file integer,
    OUT inserted     integer,
    OUT updated      integer,
    OUT skipped      integer
)
LANGUAGE plpgsql AS $$
BEGIN
    SELECT count(*) INTO rows_in_file FROM stage_agri_enterprises;

    DROP TABLE IF EXISTS stage_agri_enterprises_clean;
    CREATE TEMP TABLE stage_agri_enterprises_clean ON COMMIT DROP AS
    SELECT DISTINCT ON (edrpou, address) *
    FROM (
        SELECT lpad(trim(edrpou), 8, '0')   AS edrpou,
               trim(name)                   AS name,
               nullif(trim(address), '')    AS address,
               nullif(trim(director), '')   AS director,
               nullif(trim(kved), '')       AS kved
        FROM stage_agri_enterprises
        WHERE nullif(trim(edrpou), '') IS NOT NULL
    ) s
    ORDER BY edrpou, address;

    WITH upsert AS (
        INSERT INTO agri_enterprises AS t (edrpou, name, address, director, kved, source_file)
        SELECT edrpou, name, address, director, kved, p_source_file
        FROM stage_agri_enterprises_clean
        ON CONFLICT ON CONSTRAINT agri_enterprises_edrpou_address_uq DO UPDATE
            SET name        = EXCLUDED.name,
                director    = EXCLUDED.director,
                kved        = EXCLUDED.kved,
                source_file = EXCLUDED.source_file,
                imported_at = now()
            WHERE (t.name, t.director, t.kved)
                  IS DISTINCT FROM (EXCLUDED.name, EXCLUDED.director, EXCLUDED.kved)
        RETURNING (xmax = 0) AS is_insert
    )
    SELECT count(*) FILTER (WHERE is_insert), count(*) FILTER (WHERE NOT is_insert)
    INTO inserted, updated
    FROM upsert;

    skipped := rows_in_file - inserted - updated;
END;
$$;
