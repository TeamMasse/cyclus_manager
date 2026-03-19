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
    return [{"id": row[0], "Firstname": row[1], "Surname": row[2], "Date of birth": row[3], "Gender": row[4], "Body weight": row[5], "Body height": row[6], "Drag area": row[7], "Drag coefficient": row[8]} for row in rows]

@app.get("/bicycles")
def list_bicycles():
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM bicycles;")
            rows = cur.fetchall()
    return [{"id": row[0], "Label": row[1], "Wheel size": row[2], "Crank length": row[3], "Weight": row[4], "Chainring size": row[5], "Sprocket size": row[6]} for row in rows]