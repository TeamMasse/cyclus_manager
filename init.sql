CREATE TABLE users (
    "id" serial PRIMARY KEY,
    "first_name" character varying(32) NOT NULL,
    "last_name" character varying(32) NOT NULL,
    "date_of_birth" date NOT NULL,
    "gender" smallint DEFAULT 0 CHECK ("gender" IN (0, 1, 2)),
    "body_weight_kg" real NOT NULL,
    "body_height_m" real NOT NULL,
    "drag_area_m2" real NOT NULL,
    "drag_coefficient" real NOT NULL
);

CREATE TABLE bicycles (
    "id" serial PRIMARY KEY,
    "label" character varying(64) NOT NULL,
    "wheel_size_m" real DEFAULT 0.68,
    "crank_length_m" real NOT NULL,
    "weight_kg" real DEFAULT 6.8,
    "chainring_size" smallint NOT NULL,
    "sprocket_size" smallint DEFAULT 12
);

CREATE TABLE workouts (
    "id" serial PRIMARY KEY,
    "user_id" integer NOT NULL REFERENCES users("id") ON DELETE CASCADE,
    "bicycle_id" integer NOT NULL REFERENCES bicycles("id") ON DELETE CASCADE,
    "date" date NOT NULL,
    "duration_s" int NOT NULL,
    "distance_km" real NOT NULL,
    "average_speed_kmh" real NOT NULL,
    "average_power_w" real NOT NULL,
    "file_path" character varying(256) NOT NULL
);