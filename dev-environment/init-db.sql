CREATE USER "toldbehandling-ui" WITH PASSWORD 'toldbehandling' CREATEDB;
CREATE DATABASE "toldbehandling-ui";
GRANT ALL PRIVILEGES ON DATABASE "toldbehandling-ui" TO "toldbehandling-ui";
ALTER DATABASE "toldbehandling-ui" OWNER TO "toldbehandling-ui";
GRANT ALL ON SCHEMA "public" TO "toldbehandling-ui";

CREATE USER "toldbehandling-admin" WITH PASSWORD 'toldbehandling' CREATEDB;
CREATE DATABASE "toldbehandling-admin";
GRANT ALL PRIVILEGES ON DATABASE "toldbehandling-admin" TO "toldbehandling-admin";
ALTER DATABASE "toldbehandling-admin" OWNER TO "toldbehandling-admin";
GRANT ALL ON SCHEMA "public" TO "toldbehandling-admin";
