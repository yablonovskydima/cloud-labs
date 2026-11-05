-- Tables for importing open data (data.gov.ua) from an S3 bucket into PostgreSQL (RDS).
--
-- 1) city_routes      <- CSV  "List of carriers providing urban electric and road passenger
--                              transport services" (Transport and Communications Department
--                              of Ivano-Frankivsk City Council), resource routes.csv
--                              (GTFS routes format, ';' delimiter).
-- 2) agri_enterprises <- JSON "List of agricultural enterprises of Ivano-Frankivsk region"
--                              (Ivano-Frankivsk Regional State Administration),
--                              resource perelik-sg-gospodarstv2023.json.
--
-- The source files are in .gitignore (samples/) and are not committed. Download them into samples/:
--   samples/if_city_routes.csv:
--     https://data.gov.ua/dataset/d8883f22-c3d5-4787-9466-0d14788ef808/resource/c3fe9350-189e-44c1-8dd8-1cce883b1eb0/download/routes.csv
--   samples/if_agri_enterprises_2023.json:
--     https://data.gov.ua/dataset/24fb62b1-c624-4fce-ae7f-37a05477a789/resource/2e0f3372-b71c-41c0-9024-d5825669f2e5/download/perelik-sg-gospodarstv2023.json

BEGIN;

CREATE TABLE IF NOT EXISTS city_routes (
    id           bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    route_uid    integer      NOT NULL,
    agency_id    varchar(10)  NOT NULL,
    short_name   varchar(16)  NOT NULL,
    full_name    varchar(255) NOT NULL,
    description  text,
    route_type   smallint     NOT NULL,
    homepage     varchar(255),
    colour       varchar(32),
    text_colour  varchar(32),
    sort_order   integer,
    source_file  varchar(1024) NOT NULL,
    imported_at  timestamptz  NOT NULL DEFAULT now(),

    CONSTRAINT city_routes_type_chk CHECK (route_type BETWEEN 0 AND 12),
    CONSTRAINT city_routes_uid_per_file_uq UNIQUE (source_file, route_uid)
);

CREATE INDEX IF NOT EXISTS city_routes_agency_idx     ON city_routes (agency_id);
CREATE INDEX IF NOT EXISTS city_routes_short_name_idx ON city_routes (short_name);


CREATE TABLE IF NOT EXISTS agri_enterprises (
    id           bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    edrpou       char(8)      NOT NULL,
    name         varchar(500) NOT NULL,
    address      varchar(500),
    director     varchar(255),
    kved         varchar(255),
    source_file  varchar(1024) NOT NULL,
    imported_at  timestamptz  NOT NULL DEFAULT now(),

    CONSTRAINT agri_enterprises_edrpou_chk CHECK (edrpou ~ '^[0-9]{8}$')
);

CREATE INDEX IF NOT EXISTS agri_enterprises_edrpou_idx ON agri_enterprises (edrpou);
CREATE INDEX IF NOT EXISTS agri_enterprises_source_idx ON agri_enterprises (source_file);

COMMIT;
