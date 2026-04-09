import asyncio
import json
import os
import redis.asyncio as redis

# Globals for device state
devices = {}

class ErgometerDevice:
    def __init__(self, label, ip, port, redis_client):
        self.label = label
        self.ip = ip
        self.port = port
        self.redis = redis_client
        self.writer = None
        self.lock = asyncio.Lock() # Ensures one command at a time

    async def connect_and_listen(self):
        while True:
            print(f"[{self.label}] Connecting to {self.ip}:{self.port}...")
            try:
                reader, self.writer = await asyncio.open_connection(self.ip, self.port)
                print(f"[{self.label}] Connected!")

                while True:
                    data = await reader.readuntil(b'\n')
                    if not data:
                        break
                    
                    decoded = data.decode('utf-8').strip()
                    
                    # If the lock is LOCKED, a command is currently waiting for this exact line of data!
                    # If it's UNLOCKED, it's just normal passive telemetry.
                    if self.lock.locked():
                        self._last_response = decoded
                    else:
                        # Publish passive telemetry to Redis for the UI to consume
                        await self.redis.publish(f"ergo/telemetry/{self.label}", decoded)
                        # print(f"[{self.label}] Telemetry: {decoded}")

            except Exception as e:
                print(f"[{self.label}] Error: {e}")
            finally:
                self.writer = None
                print(f"[{self.label}] Disconnected. Reconnecting in 5s...")
                await asyncio.sleep(5)

    async def execute_command(self, cmd_data):
        if not self.writer:
            return {"error": "Not connected"}
        
        # 1. Lock the device so telemetry is paused and other commands wait
        async with self.lock:
            self._last_response = None
            try:
                # 2. Send command
                command_str = cmd_data['command']
                self.writer.write(f"{command_str}\n".encode('utf-8'))
                await self.writer.drain()
                
                # 3. Wait for the reading loop to populate _last_response
                for _ in range(30): # 3-second timeout (30 * 0.1s)
                    if self._last_response is not None:
                        return {"response": self._last_response}
                    await asyncio.sleep(0.1)
                    
                return {"error": "Timeout waiting for ergometer response"}
            except Exception as e:
                return {"error": str(e)}

async def listen_for_commands(redis_client):
    """Listens to Redis for commands coming from FastAPI."""
    pubsub = redis_client.pubsub()
    await pubsub.subscribe("ergo/commands")
    print("Listening for API commands on Redis...")
    
    async for message in pubsub.listen():
        if message['type'] == 'message':
            data = json.loads(message['data'])
            label = data['label']
            req_id = data['req_id'] # Unique ID so FastAPI knows which request this is
            
            if label in devices:
                # Execute the command on the specific device
                result = await devices[label].execute_command(data)
                
                # Publish the result back to Redis specifically for FastAPI to catch
                reply = {"req_id": req_id, **result}
                await redis_client.publish(f"ergo/responses/{label}", json.dumps(reply))

async def main():
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    redis_client = redis.from_url(redis_url)
    
    config = json.loads(os.getenv("ERGOMETERS_CONFIG", "{}"))
    
    # Start device loops
    for label, ip_port in config.items():
        ip, port = ip_port.split(':')
        devices[label] = ErgometerDevice(label, ip, int(port), redis_client)
        asyncio.create_task(devices[label].connect_and_listen())

    # Start command listener
    await listen_for_commands(redis_client)

if __name__ == "__main__":
    asyncio.run(main())