import os
from datetime import datetime
import psycopg
from contextlib import asynccontextmanager
import asyncio
import json
import uuid
import redis.asyncio as redis
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Global Redis client
redis_client = None
ENV_DATABASE_URL = os.getenv("DATABASE_URL")

@asynccontextmanager
async def lifespan(app: FastAPI):
    global redis_client
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    redis_client = redis.from_url(redis_url)
    yield
    await redis_client.close()

app = FastAPI(lifespan=lifespan)

class CommandRequest(BaseModel):
    command: str
    
class LoadPlanRequest(BaseModel):
    plan_id: int

@app.post("/api/ergometers/{label}/command")
async def send_ergometer_command(label: str, req: CommandRequest):
    req_id = str(uuid.uuid4()) # Create a unique ID for this HTTP request
    
    # 1. Subscribe to the response channel BEFORE sending the command
    pubsub = redis_client.pubsub()
    await pubsub.subscribe(f"ergo/responses/{label}")
    
    # 2. Publish the command to the Device Manager
    payload = {"label": label, "command": req.command, "req_id": req_id}
    await redis_client.publish("ergo/commands", json.dumps(payload))
    
    # 3. Wait for the specific response to come back
    async def wait_for_response():
        async for message in pubsub.listen():
            if message['type'] == 'message':
                data = json.loads(message['data'])
                # Ensure this response belongs to THIS http request
                if data.get('req_id') == req_id:
                    return data
    try:
        # Timeout after 5.5 seconds
        result = await asyncio.wait_for(wait_for_response(), timeout=5.5)
        await pubsub.unsubscribe()
        
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
            
        return {"status": "success", "response": result.get("response")}
        
    except asyncio.TimeoutError:
        await pubsub.unsubscribe()
        raise HTTPException(status_code=504, detail="Timeout waiting for Device Manager")

@app.post("/api/ergometers/{label}/time")
async def set_ergometer_time(label: str):
    response = await send_ergometer_command(label, CommandRequest(command="time=" + datetime.now().strftime("%d.%m.%Y %H:%M:%S")))
    return response

@app.post("/api/ergometers/{label}/setup")
async def setup_cyclus(label: str, user_id: int, bicycle_id: int):
    with psycopg.connect(ENV_DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM users WHERE id = %s;", (user_id,))
            user = cur.fetchone()
            response1 = await send_ergometer_command(label, CommandRequest(command=f"user1=0,{user[1]},{user[2]},{datetime.strftime(user[3], '%d.%m.%Y')},{user[4]},{user[5]},{user[6]},{user[7]},{user[8]}"))
            #print(f"Fetched user: {user}") #Fetched user: (1, 'Theo', 'Fischer', datetime.date(2006, 6, 13), 1, 95.0, 1.92, 0.5, 0.3)
            
            cur.execute("SELECT * FROM bicycles WHERE id = %s;", (bicycle_id,))
            bicycle = cur.fetchone()
            response2 = await send_ergometer_command(label, CommandRequest(command=f"cycle1=0,{bicycle[2]},{bicycle[3]},{bicycle[4]},{bicycle[5]},{bicycle[6]},{bicycle[5]},{bicycle[6]}"))
            #print(f"Fetched bicycle: {bicycle}") #Fetched bicycle: (1, 'FES', 0.68, 0.17, 6.8, 57, 12)
            
    return {"id": label, "user_response": response1, "bicycle_response": response2}

@app.post("/api/ergometers/{label}/load_plan")
async def load_training_plan(label: str, req: LoadPlanRequest):
    req_id = str(uuid.uuid4()) # Create a unique ID for this HTTP request
    
    # 1. Subscribe to the response channel BEFORE sending the command
    pubsub = redis_client.pubsub()
    await pubsub.subscribe(f"ergo/responses/{label}")
    
    # 2. Publish the command to the Device Manager
    payload = {"label": label, "plan_id": req.plan_id, "req_id": req_id}
    await redis_client.publish("ergo/load_plan", json.dumps(payload))
    
    # 3. Wait for the specific response to come back
    async def wait_for_response():
        async for message in pubsub.listen():
            if message['type'] == 'message':
                data = json.loads(message['data'])
                # Ensure this response belongs to THIS http request
                if data.get('req_id') == req_id:
                    return data
    try:
        # Timeout after 5.5 seconds
        result = await asyncio.wait_for(wait_for_response(), timeout=5.5)
        await pubsub.unsubscribe()
        
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
            
        return {"status": "success", "response": result.get("response")}
        
    except asyncio.TimeoutError:
        await pubsub.unsubscribe()
        raise HTTPException(status_code=504, detail="Timeout waiting for Device Manager")

@app.get("/health")
def health():
    return {"status": "healthy"}

@app.get("/health/db")
def db_health():
    with psycopg.connect(ENV_DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1;")
            return {"db_ok": cur.fetchone()[0] == 1}

@app.get("/users")
def list_users():
    with psycopg.connect(ENV_DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM users;")
            rows = cur.fetchall()
    return [{"id": row[0], "first_name": row[1], "last_name": row[2], "date_of_birth": row[3], "gender": row[4], "body_weight_kg": row[5], "body_height_m": row[6], "drag_area_m2": row[7], "drag_coefficient": row[8]} for row in rows]

@app.post("/users")
def create_user(user: dict):
    with psycopg.connect(ENV_DATABASE_URL) as conn:
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

@app.put("/users/{user_id}")
def update_user(user_id: int, user: dict):
    with psycopg.connect(ENV_DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(
                '''
                UPDATE users
                SET "first_name" = %s, "last_name" = %s, "date_of_birth" = %s, "gender" = %s, "body_weight_kg" = %s, "body_height_m" = %s, "drag_area_m2" = %s, "drag_coefficient" = %s
                WHERE "id" = %s;
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
                    user_id,
                ),
            )
            conn.commit()
    return {"id": user_id, **user}

@app.delete("/users/{user_id}")
def delete_user(user_id: int):
    with psycopg.connect(ENV_DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM users WHERE id = %s;", (user_id,))
            conn.commit()
    return {"status": "deleted", "id": user_id}

@app.get("/bicycles")
def list_bicycles():
    with psycopg.connect(ENV_DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM bicycles;")
            rows = cur.fetchall()
    return [{"id": row[0], "label": row[1], "wheel_size_m": row[2], "crank_length_m": row[3], "weight_kg": row[4], "chainring_size": row[5], "sprocket_size": row[6]} for row in rows]

@app.post("/bicycles")
def create_bicycle(bicycle: dict):
    with psycopg.connect(ENV_DATABASE_URL) as conn:
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

@app.put("/bicycles/{bicycle_id}")
def update_bicycle(bicycle_id: int, bicycle: dict):
    with psycopg.connect(ENV_DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(
                '''
                UPDATE bicycles
                SET "label" = %s, "wheel_size_m" = %s, "crank_length_m" = %s, "weight_kg" = %s, "chainring_size" = %s, "sprocket_size" = %s
                WHERE "id" = %s;
                ''',
                (
                    bicycle["label"],
                    bicycle["wheel_size_m"],
                    bicycle["crank_length_m"],
                    bicycle["weight_kg"],
                    bicycle["chainring_size"],
                    bicycle["sprocket_size"],
                    bicycle_id,
                ),
            )
            conn.commit()
    return {"id": bicycle_id, **bicycle}

@app.delete("/bicycles/{bicycle_id}")
def delete_bicycle(bicycle_id: int):
    with psycopg.connect(ENV_DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM bicycles WHERE id = %s;", (bicycle_id,))
            conn.commit()
    return {"status": "deleted", "id": bicycle_id}

@app.get("/training_plans")
def list_training_plans():
    with psycopg.connect(ENV_DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM training_plans;")
            rows = cur.fetchall()
    return [{"id": row[0], "label": row[1], "plan": row[2], "duration_s": row[3]} for row in rows]

@app.post("/training_plans")
def create_training_plan(plan: dict):
    with psycopg.connect(ENV_DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(
                '''
                INSERT INTO training_plans
                ("label", "plan", "duration_s")
                VALUES (%s, %s, %s)
                RETURNING "id";
                ''',
                (
                    plan["label"],
                    plan["plan"],
                    plan["duration_s"]
                ),
            )
            plan_id = cur.fetchone()[0]
            conn.commit()
    return {"id": plan_id, **plan}

@app.put("/training_plans/{plan_id}")
def update_training_plan(plan_id: int, plan: dict):
    with psycopg.connect(ENV_DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(
                '''
                UPDATE training_plans
                SET "label" = %s, "plan" = %s, "duration_s" = %s
                WHERE "id" = %s;
                ''',
                (
                    plan["label"],
                    plan["plan"],
                    plan["duration_s"],
                    plan_id,
                ),
            )
            conn.commit()
    return {"id": plan_id, **plan}

@app.delete("/training_plans/{plan_id}")
def delete_training_plan(plan_id: int):
    with psycopg.connect(ENV_DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM training_plans WHERE id = %s;", (plan_id,))
            conn.commit()
    return {"status": "deleted", "id": plan_id}

@app.get("/training_sessions")
def list_training_sessions():
    with psycopg.connect(ENV_DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT training_sessions.id,users.first_name,bicycles.label,training_plans.label,training_sessions.date,training_sessions.duration_s,training_sessions.distance_km,training_sessions.average_speed_kmh,training_sessions.average_power_w FROM training_sessions join users on training_sessions.user_id = users.id join bicycles on training_sessions.bicycle_id = bicycles.id join training_plans on training_sessions.training_plan_id = training_plans.id;")
            rows = cur.fetchall()
    return [{"id": row[0], "user_id": row[1], "bicycle_id": row[2], "training_plan_id": row[3], "date": row[4], "duration_s": row[5], "distance_km": row[6], "average_speed_kmh": row[7], "average_power_w": row[8]} for row in rows]
