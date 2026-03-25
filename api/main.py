import asyncio
import json
import os
import psycopg
from fastapi import FastAPI

app = FastAPI()
DATABASE_URL = os.getenv("DATABASE_URL")

@app.get("/health/db")
def db_health():
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1;")
            return {"db_ok": cur.fetchone()[0] == 1}

@app.get("/users")
def list_users():
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM users;")
            rows = cur.fetchall()
    return [{"id": row[0], "first_name": row[1], "last_name": row[2], "date_of_birth": row[3], "gender": row[4], "body_weight_kg": row[5], "body_height_m": row[6], "drag_area_m2": row[7], "drag_coefficient": row[8]} for row in rows]

@app.post("/users")
def create_user(user: dict):
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(
                '''
                INSERT INTO users
                ("first_name", "last_name", "date_of_birth", "gender", "body_weight_kg", "body_height_m", "drag_area_m2", "drag_coefficient")
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING "id";
                ''',
                (
                    user["first_name"],
                    user["last_name"],
                    user["date_of_birth"],
                    user["gender"],
                    user["body_weight_kg"],
                    user["body_height_m"],
                    user["drag_area_m2"],
                    user["drag_coefficient"],
                ),
            )
            user_id = cur.fetchone()[0]
            conn.commit()
    return {"id": user_id, **user}

@app.get("/bicycles")
def list_bicycles():
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM bicycles;")
            rows = cur.fetchall()
    return [{"id": row[0], "label": row[1], "wheel_size_m": row[2], "crank_length_m": row[3], "weight_kg": row[4], "chainring_size": row[5], "sprocket_size": row[6]} for row in rows]

@app.post("/bicycles")
def create_bicycle(bicycle: dict):
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(
                '''
                INSERT INTO bicycles
                ("label", "wheel_size_m", "crank_length_m", "weight_kg", "chainring_size", "sprocket_size")
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING "id";
                ''',
                (
                    bicycle["label"],
                    bicycle["wheel_size_m"],
                    bicycle["crank_length_m"],
                    bicycle["weight_kg"],
                    bicycle["chainring_size"],
                    bicycle["sprocket_size"]
                ),
            )
            bicycle_id = cur.fetchone()[0]
            conn.commit()
    return {"id": bicycle_id, **bicycle}