import asyncio
import json
import os
from pathlib import Path
import redis.asyncio as redis
import re

# Globals for device state
devices = {}

class ErgometerDevice:
    def __init__(self, label, ip, port, redis_client, training_plans_dir):
        self.label = label
        self.ip = ip
        self.port = port
        self.redis = redis_client
        self.training_plans_dir = Path(training_plans_dir)
        self.writer = None
        self.lock = asyncio.Lock() # Ensures one command at a time
        self._pending_response = None
        self._response_event = asyncio.Event()
        self.telemetry_enabled = False
        self._telemetry_task = None
        self._last_telemetry_line = None

    @staticmethod
    def _is_telemetry_line(line):
        return line.startswith("data:")

    async def _publish_telemetry_if_new(self, line):
        if line == self._last_telemetry_line:
            #print(f"[{self.label}] telemetry duplicate skipped: {line!r}")
            return False

        self._last_telemetry_line = line
        await self.redis.publish(f"ergo/telemetry/{self.label}", line)
        return True

    @staticmethod
    async def _read_device_line(reader):
        chunks = []
        while True:
            chunk = await reader.read(1)
            if not chunk:
                if not chunks:
                    return None
                break
            if chunk in (b"\r", b"\n"):
                break
            chunks.append(chunk)

        return b"".join(chunks).decode("utf-8", errors="replace")

    async def _send_line_locked(self, line, timeout_s=5.0):
        if not self.writer:
            #print(f"[{self.label}] _send_line_locked: not connected, line={line!r}")
            return {"error": "Not connected"}

        #print(f"[{self.label}] _send_line_locked: writer={self.writer!r} sending line={line!r} timeout_s={timeout_s}")
        self._pending_response = None
        self._response_event.clear()
        try:
            self.writer.write(f"{line}\r\n".encode('utf-8'))
            await self.writer.drain()

            #print(f"[{self.label}] _send_line_locked: waiting for ack/response")
            await asyncio.wait_for(self._response_event.wait(), timeout=timeout_s)

            response = (self._pending_response or "").strip()
            self._pending_response = None
            rl = response.lower()
            #print(f"[{self.label}] _send_line_locked: got response={response!r}")
            # Accept 'ok' even if prefixed by prompt text like 'cli> ok'
            if re.search(r"\bok\b", rl):
                return {"response": "ok"}
            # Accept 'error:' anywhere in the response
            m = re.search(r"error:\s*(.*)", rl)
            if m:
                msg = m.group(1).strip() or response
                return {"error": msg}

            return {"error": f"Unexpected ergometer response: {response}"}
        except asyncio.TimeoutError:
            return {"error": "Timeout waiting for ergometer acknowledgement"}
        except Exception as e:
            return {"error": str(e)}

    async def connect_and_listen(self):
        while True:
            print(f"[{self.label}] Connecting to {self.ip}:{self.port}...")
            try:
                reader, self.writer = await asyncio.open_connection(self.ip, self.port)
                print(f"[{self.label}] Connected!")

                while True:
                    decoded = await self._read_device_line(reader)
                    if decoded is None:
                        break
                    if not decoded:
                        continue
                    #print(f"[{self.label}] RX: {decoded!r} lock={self.lock.locked()} pending={self._pending_response is not None}")

                    if self._is_telemetry_line(decoded):
                        await self._publish_telemetry_if_new(decoded)
                        continue

                    # Non-telemetry lines are treated as command responses while a command is active.
                    if self.lock.locked() and self._pending_response is None:
                        self._pending_response = decoded
                        #print(f"[{self.label}] RX stored as pending response: {decoded!r}")
                        self._response_event.set()
                        #print(f"[{self.label}] response event set")
                    else:
                        print(f"[{self.label}] RX ignored (non-telemetry, idle or already handled): {decoded!r}")

            except Exception as e:
                print(f"[{self.label}] Error: {e}")
            finally:
                self.writer = None
                # Mark telemetry disabled on disconnect so ensure_telemetry_enabled will retry
                self.telemetry_enabled = False
                print(f"[{self.label}] Disconnected. Reconnecting in 5s...")
                await asyncio.sleep(5)

    def request_telemetry_enable(self):
        """Schedule telemetry enablement once, after the first successful command."""
        if self.telemetry_enabled or self._telemetry_task is not None:
            return

        print(f"[{self.label}] scheduling telemetry enable task")
        self._telemetry_task = asyncio.create_task(self.ensure_telemetry_enabled())

    async def ensure_telemetry_enabled(self):
        """Background task: enable telemetry after the controller has already handled a command."""
        while True:
            # wait until connected and the controller is idle
            while self.writer is None:
                print(f"[{self.label}] ensure_telemetry_enabled: waiting for connection")
                await asyncio.sleep(0.5)

            while self.lock.locked():
                print(f"[{self.label}] ensure_telemetry_enabled: waiting for lock to clear")
                await asyncio.sleep(0.1)

            # try to enable telemetry, respecting the device lock
            try:
                async with self.lock:
                    print(f"[{self.label}] ensure_telemetry_enabled: trying data=7")
                    # Retry a few times if the device doesn't ack immediately
                    for _ in range(5):
                        res = await self._send_line_locked("data=7", timeout_s=5.0)
                        print(f"[{self.label}] ensure_telemetry_enabled: data=7 result={res}")
                        if res.get("response") == "ok":
                            self.telemetry_enabled = True
                            print(f"[{self.label}] ensure_telemetry_enabled: telemetry enabled")
                            break
                        await asyncio.sleep(1)
                    break
            except Exception:
                print(f"[{self.label}] ensure_telemetry_enabled: exception while enabling telemetry")
                pass

            # Wait until disconnected before trying again
            while self.writer is not None:
                await asyncio.sleep(0.5)

        self._telemetry_task = None

    async def execute_command(self, cmd_data):
        # 1. Lock the device so telemetry is paused and other commands wait
        command = cmd_data.get('command') if isinstance(cmd_data, dict) else cmd_data
        print(f"[{self.label}] execute_command: command={command!r}")
        async with self.lock:
            # Queries ending with '?' should return whatever the device replies (not an ok/error ack)
            if isinstance(command, str) and command.strip().endswith('?'):
                #print(f"[{self.label}] execute_command: query path")
                result = await self._send_and_receive(command)
            else:
                #print(f"[{self.label}] execute_command: ack-gated path")
                # Otherwise use ack-gated send
                result = await self._send_line_locked(command)

            if not self.telemetry_enabled and self._telemetry_task is None and "error" not in result:
                print(f"[{self.label}] execute_command: requesting telemetry enable after success")
                self.request_telemetry_enable()

            print(f"[{self.label}] execute_command: result={result}")
            return result

    async def _send_and_receive(self, line, timeout_s=5.0):
        """Send a line and wait for the first response line (used for queries ending with '?')."""
        if not self.writer:
            print(f"[{self.label}] _send_and_receive: not connected, line={line!r}")
            return {"error": "Not connected"}

        print(f"[{self.label}] _send_and_receive: writer={self.writer!r} sending query line={line!r}")
        self._pending_response = None
        self._response_event.clear()
        try:
            self.writer.write(f"{line}\r\n".encode('utf-8'))
            await self.writer.drain()

            print(f"[{self.label}] _send_and_receive: waiting for first response")
            await asyncio.wait_for(self._response_event.wait(), timeout=timeout_s)
            response = (self._pending_response or "").strip()
            self._pending_response = None
            print(f"[{self.label}] _send_and_receive: got response={response!r}")
            return {"response": response}
        except asyncio.TimeoutError:
            print(f"[{self.label}] _send_and_receive: timeout waiting for response")
            return {"error": "Timeout waiting for ergometer response"}
        except Exception as e:
            print(f"[{self.label}] _send_and_receive: exception={e!r}")
            return {"error": str(e)}

    async def load_plan(self, plan_id):
        plan_path = self.training_plans_dir / f"{plan_id}.stages"
        print(f"[{self.label}] load_plan: plan_id={plan_id} path={plan_path}")

        async with self.lock:
            if not self.writer:
                print(f"[{self.label}] load_plan: not connected")
                return {"error": "Not connected"}

            try:
                with plan_path.open("r", encoding="utf-8") as plan_file:
                    for raw_line in plan_file:
                        line = raw_line.rstrip("\r\n")
                        print(f"[{self.label}] load_plan: sending stage line={line!r}")
                        # stage lines may start with 'stage:' or 'stage='; send them as ack-gated commands
                        result = await self._send_line_locked(line)
                        print(f"[{self.label}] load_plan: stage line result={result}")
                        if "error" in result:
                            return result

                if not self.telemetry_enabled and self._telemetry_task is None:
                    print(f"[{self.label}] load_plan: requesting telemetry enable after plan")
                    self.request_telemetry_enable()

                print(f"[{self.label}] load_plan: completed successfully")
                return {"response": f"Loaded plan {plan_id}"}
            except FileNotFoundError:
                print(f"[{self.label}] load_plan: missing file {plan_path}")
                return {"error": f"Training plan not found: {plan_path}"}
            except Exception as e:
                print(f"[{self.label}] load_plan: exception={e!r}")
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
            print(f"[controller] ergo/commands label={label!r} req_id={req_id!r} payload={data}")
            
            if label in devices:
                # Execute the command on the specific device
                result = await devices[label].execute_command(data)
            else:
                result = {"error": f"Unknown ergometer label: {label}"}
                
            # Publish the result back to Redis specifically for FastAPI to catch
            reply = {"req_id": req_id, **result}
            await redis_client.publish(f"ergo/responses/{label}", json.dumps(reply))


async def listen_for_load_plans(redis_client):
    """Listens to Redis for training plan load requests coming from FastAPI."""
    pubsub = redis_client.pubsub()
    await pubsub.subscribe("ergo/load_plan")
    print("Listening for API load-plan requests on Redis...")

    async for message in pubsub.listen():
        if message['type'] == 'message':
            data = json.loads(message['data'])
            label = data['label']
            req_id = data['req_id']
            plan_id = data['plan_id']
            print(f"[controller] ergo/load_plan label={label!r} req_id={req_id!r} plan_id={plan_id!r}")

            if label in devices:
                result = await devices[label].load_plan(plan_id)
            else:
                result = {"error": f"Unknown ergometer label: {label}"}

            reply = {"req_id": req_id, **result}
            await redis_client.publish(f"ergo/responses/{label}", json.dumps(reply))

async def main():
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    redis_client = redis.from_url(redis_url)
    training_plans_dir = os.getenv("TRAINING_PLANS_DIR", "/training_plans")
    print(f"[controller] starting with REDIS_URL={redis_url!r} TRAINING_PLANS_DIR={training_plans_dir!r}")
    
    config = json.loads(os.getenv("ERGOMETERS_CONFIG", "{}"))
    print(f"[controller] ERGOMETERS_CONFIG keys={list(config.keys())}")
    
    # Start device loops
    for label, ip_port in config.items():
        ip, port = ip_port.split(':')
        print(f"[controller] creating device label={label!r} target={ip}:{port}")
        devices[label] = ErgometerDevice(label, ip, int(port), redis_client, training_plans_dir)
        asyncio.create_task(devices[label].connect_and_listen())

    # Start command listeners
    await asyncio.gather(
        listen_for_commands(redis_client),
        listen_for_load_plans(redis_client),
    )

if __name__ == "__main__":
    asyncio.run(main())