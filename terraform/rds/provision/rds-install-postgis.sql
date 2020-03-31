-- this is taken from the AWS docs
-- https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/Appendix.PostgreSQL.CommonDBATasks.html#Appendix.PostgreSQL.CommonDBATasks.PostGIS
create extension postgis;
create extension fuzzystrmatch;
create extension postgis_tiger_geocoder;
create extension postgis_topology;

alter schema tiger owner to rds_superuser;
alter schema tiger_data owner to rds_superuser;
alter schema topology owner to rds_superuser;

CREATE FUNCTION exec(text) returns text language plpgsql volatile AS $f$ BEGIN EXECUTE $1; RETURN $1; END; $f$;

SELECT exec('ALTER TABLE ' || quote_ident(s.nspname) || '.' || quote_ident(s.relname) || ' OWNER TO rds_superuser;')
  FROM (
    SELECT nspname, relname
    FROM pg_class c JOIN pg_namespace n ON (c.relnamespace = n.oid)
    WHERE nspname in ('tiger','topology') AND
    relkind IN ('r','S','v') ORDER BY relkind = 'S')
s;

CREATE DATABASE trees;

-- Sequence and defined type
CREATE SEQUENCE IF NOT EXISTS radolan_harvester_id_seq;

-- Table Definition
CREATE TABLE "public"."radolan_harvester" (
    "id" int4 NOT NULL DEFAULT nextval('radolan_harvester_id_seq'::regclass),
    "collection_date" date,
    "start_date" timestamp,
    "end_date" timestamp,
    PRIMARY KEY ("id")
);

CREATE SEQUENCE IF NOT EXISTS radolan_geometry_id_seq;

-- Table Definition
CREATE TABLE "public"."radolan_geometry" (
    "id" int4 NOT NULL DEFAULT nextval('radolan_geometry_id_seq'::regclass),
    "geometry" geometry,
    "centroid" geometry,
    PRIMARY KEY ("id")
);

-- Sequence and defined type
CREATE SEQUENCE IF NOT EXISTS radolan_temp_id_seq;

-- Table Definition
CREATE TABLE "public"."radolan_temp" (
    "id" int4 NOT NULL DEFAULT nextval('radolan_temp_id_seq'::regclass),
    "geometry" geometry,
    "value" int2,
    "measured_at" timestamp,
    PRIMARY KEY ("id")
);


-- Sequence and defined type
CREATE SEQUENCE IF NOT EXISTS trees_watered_id_seq;

-- Table Definition
CREATE TABLE "public"."trees_watered" (
    "id" text NOT NULL DEFAULT nextval('trees_watered_id_seq'::regclass),
    "watered" _text DEFAULT '{}'::text[],
    PRIMARY KEY ("id")
);
CREATE TABLE "public"."trees" (
    "id" text NOT NULL,
    "lat" text,
    "lng" text,
    "artDtsch" text,
    "artBot" text,
    "gattungDeutsch" text,
    "gattung" text,
    "strName" text,
    "hausNr" text,
    "zusatz" text,
    "pflanzjahr" int4,
    "standAlter" text,
    "kroneDurch" text,
    "stammUmfg" text,
    "type" text,
    "baumHoehe" text,
    "bezirk" text,
    "eigentuemer" text,
    "adopted" text,
    "watered" text,
    "radolan_sum" int4,
    "radolan_days" _int4,
    "geom" geometry,
    PRIMARY KEY ("id")
);
-- This script only contains the table creation statements and does not fully represent the table in the database. It's still missing: indices, triggers. Do not use it as a backup.

-- Sequence and defined type
CREATE SEQUENCE IF NOT EXISTS radolan_data_id_seq;

-- Table Definition
CREATE TABLE "public"."radolan_data" (
    "id" int4 NOT NULL DEFAULT nextval('radolan_data_id_seq'::regclass),
    "measured_at" timestamp,
    "value" int2,
    "geom_id" int2,
    PRIMARY KEY ("id")
);

INSERT INTO "public"."trees" ("id", "lat", "lng", "artDtsch", "artBot", "gattungDeutsch", "gattung", "strName", "hausNr", "zusatz", "pflanzjahr", "standAlter", "kroneDurch", "stammUmfg", "type", "baumHoehe", "bezirk", "eigentuemer", "adopted", "watered", "radolan_sum", "radolan_days", "geom") VALUES
('_0003jj0vy', '13.4052', '52.4077', 'Winter-Linde', 'Tilia cordata', 'LINDE', 'TILIA', 'Lichtenrader Damm', '67', 'null', '1969', '50', 'null', '172', 'strasse', 'null', 'Tempelhof-Schöneberg', 'Land Berlin', NULL, NULL, '321', '{0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,3,4,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,6,40,0,0,0,0,0,4,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,7,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,25,11,10,2,4,0,0,0,0,14,4,0,0,2,29,2,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,6,2,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,2,2,1,2,6,8,0,0,8,10,7,16,0,0,0,12,13,6,6,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,4,2,1,0,0,0,0,0,8,0,3,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,3,2,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,3,2,0,6,6,0,0,0,0,0,0,0,0,0,0}', 'SRID=4326;POINT(13.4052 52.4077)');

INSERT INTO "public"."radolan_harvester" ("id", "collection_date", "start_date", "end_date") VALUES
('1', '2020-03-29', '2020-02-29 00:50:00', '2020-03-29 23:50:00');