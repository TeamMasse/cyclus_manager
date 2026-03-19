CREATE TABLE users (
    "ID" serial PRIMARY KEY,
    "Firstname" character varying(32) NOT NULL,
    "Surname" character varying(32) NOT NULL,
    "Date of birth" date NOT NULL,
    "Gender" smallint DEFAULT 0 NOT NULL CHECK ("Gender" IN (0, 1, 2)),
    "Body weight" real NOT NULL,
    "Body height" real NOT NULL,
    "Drag area" real NOT NULL,
    "Drag coefficient" real NOT NULL
);

CREATE TABLE bicycles (
    "ID" serial PRIMARY KEY,
    "Label" character varying(64) NOT NULL,
    "Wheel size" real DEFAULT 0.68 NOT NULL,
    "Crank length" real NOT NULL,
    "Weight" real DEFAULT 6.8 NOT NULL,
    "Chainring size" smallint NOT NULL,
    "Sprocket size" smallint DEFAULT 12 NOT NULL
);