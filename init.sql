-- Connect to the new database (in psql: \c fitin50)
CREATE DATABASE fitin50;

-- Now connect to the database
\c fitin50


CREATE TABLE IF NOT EXISTS workouts (
    id                  SERIAL PRIMARY KEY,
    folder_name         VARCHAR(64) NOT NULL,
    filename            TEXT NOT NULL,
    email            TEXT NOT NULL,
    steps               INTEGER,
    calories_kcal       DOUBLE PRECISION,
    distance_km         DOUBLE PRECISION,
    active_time_minutes DOUBLE PRECISION,
    workout_type        VARCHAR(32),
	total_points               INTEGER,
    created_at          TIMESTAMP DEFAULT NOW()
);



