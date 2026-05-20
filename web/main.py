# import plotly.graph_objects as go
import os
import json
from nicegui import events, app, ui
import httpx
import redis.asyncio as redis

# --- Global State ---
# This holds the live telemetry data for all ergometers
live_data = {}
data_version = {}
for key in json.loads(os.getenv("ERGOMETERS_CONFIG", "{}")).keys():
    live_data[key] = {
        "time": [],
        "distance": [],
        "crank_rotations": [],
        "work": [],
        "cadence": [],
        "heart_rate": [],
        "speed": [],
        "transmission": [],
        "pedal_force": [],
        "power": [],
        "inclination": [],
        "work_per_heatbeat": [],
        "virtual_chainring": [],
        "virtual_sprocket": [],
    }
    data_version[key] = 0


# --- Background Task: Listen to Redis ---
async def redis_listener():
    """
    Runs in the background, reading Redis and updating the global state.
    """

    r = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))
    pubsub = r.pubsub()

    # Subscribe to all telemetry channels using a wildcard pattern
    await pubsub.psubscribe("ergo/telemetry/*")
    print("NiceGUI connected to Redis telemetry stream.")

    try:
        async for message in pubsub.listen():
            if message["type"] == "pmessage":
                # Extract which ergo this is from the channel name
                channel = message["channel"].decode("utf-8")
                label = channel.split("/")[-1]  # e.g., "Ergo1"

                # Assume your Controller publishes JSON like: {"watts": 250, "rpm": 90}
                raw_data = message["data"].decode("utf-8")
                print(f"Received telemetry for {label}: {raw_data}")
                telemetry = raw_data[7:].split(
                    ","
                )  # Adjust parsing based on your actual data format

                # Update global state
                if label in live_data:
                    live_data[label]["time"].append(int(telemetry[0]))
                    live_data[label]["distance"].append(float(telemetry[1]))
                    live_data[label]["crank_rotations"].append(float(telemetry[2]))
                    live_data[label]["work"].append(float(telemetry[3]))
                    live_data[label]["cadence"].append(float(telemetry[4]))
                    live_data[label]["heart_rate"].append(float(telemetry[5]))
                    live_data[label]["speed"].append(float(telemetry[6]))
                    live_data[label]["transmission"].append(float(telemetry[7]))
                    live_data[label]["pedal_force"].append(float(telemetry[8]))
                    live_data[label]["power"].append(float(telemetry[9]))
                    live_data[label]["inclination"].append(float(telemetry[10]))
                    live_data[label]["work_per_heatbeat"].append(float(telemetry[11]))
                    live_data[label]["virtual_chainring"].append(int(telemetry[12]))
                    live_data[label]["virtual_sprocket"].append(int(telemetry[13]))
                    data_version[label] += 1

                    if len(live_data[label]["time"]) > 3600:
                        live_data[label]["time"].pop(0)
                        live_data[label]["distance"].pop(0)
                        live_data[label]["crank_rotations"].pop(0)
                        live_data[label]["work"].pop(0)
                        live_data[label]["cadence"].pop(0)
                        live_data[label]["heart_rate"].pop(0)
                        live_data[label]["speed"].pop(0)
                        live_data[label]["transmission"].pop(0)
                        live_data[label]["pedal_force"].pop(0)
                        live_data[label]["power"].pop(0)
                        live_data[label]["inclination"].pop(0)
                        live_data[label]["work_per_heatbeat"].pop(0)
                        live_data[label]["virtual_chainring"].pop(0)
                        live_data[label]["virtual_sprocket"].pop(0)

    except Exception as e:
        print(f"Redis listener crashed: {e}")


app.on_startup(redis_listener)

app.colors(
    primary="#575757",
    secondary="#26a69a",
    accent="#2732b0",
    dark="#1e1e1e",
    dark_page="#121212",
    positive="#21ba45",
    negative="#c10015",
    info="#31ccec",
    warning="#ff0000",
)


DEFAULT_LEGEND_SELECTED = {
    "Distance": False,
    "Crank Rotations": False,
    "Work": False,
    "Cadence": True,
    "Heart Rate": True,
    "Speed": True,
    "Transmission": False,
    "Pedal Force": False,
    "Power": True,
    "Inclination": False,
}


def page_header_title(title):
    """
    Creates a header for the page.

    :param title: The title for the page
    """
    ui.dark_mode(True)
    ui.page_title("Cyclus Manager")

    # Header with toggle button for the left drawer
    with ui.header():
        ui.button(on_click=lambda: left_drawer.toggle(), icon="menu")
        ui.label(title).style("font-size: 24px;")

    # Left drawer with navigation links
    with ui.left_drawer(fixed=True).props("width=100") as left_drawer:
        ui.link("Home", "/").style(
            "display: block; margin-bottom: 5px; color: white; text-decoration-line: none"
        )
        ui.link("Settings", "/settings").style(
            "display: block; margin-bottom: 5px; color: white; text-decoration-line: none"
        )
        ui.link("Athletes", "/athletes").style(
            "display: block; margin-bottom: 5px; color: white; text-decoration-line: none"
        )
        ui.link("Bikes", "/bikes").style(
            "display: block; margin-bottom: 5px; color: white; text-decoration-line: none"
        )
        ui.link("Training Plans", "/training_plans").style(
            "display: block; margin-bottom: 5px; color: white; text-decoration-line: none"
        )
        ui.link("Training Sessions", "/training_sessions").style(
            "display: block; margin-bottom: 5px; color: white; text-decoration-line: none"
        )


def create_api_table(api_url: str, fields: list):
    """
    Creates a NiceGUI editable table linked to a REST API.

    :param api_url: The base endpoint for the resource (e.g., 'http://localhost:8000/api/athletes')
    :param fields: List of dicts defining columns, e.g., [{'name': 'age', 'label': 'Age', 'type': 'number'}]
    """

    # 1. Transform the provided fields into NiceGUI's column format
    table_columns = []
    for f in fields:
        table_columns.append(
            {
                "name": f["name"],
                "label": f["label"],
                "field": f["name"],
                "align": f.get("align", "left"),
            }
        )

    # Initialize the table empty
    table = ui.table(columns=table_columns, rows=[], row_key="id").classes("w-full")

    # 2. Dynamically build the Vue Template for the table body
    body_html = """
    <q-tr :props="props">
        <q-td auto-width>
            <q-btn size="sm" color="warning" round dense icon="delete"
                @click="() => $parent.$emit('delete', props.row)"
            />
        </q-td>
    """

    for f in fields:
        field_name = f["name"]
        col_type = f.get("type", "text")

        # Use different Vue inputs based on data type
        if col_type == "number":
            input_tag = '<q-input v-model.number="scope.value" type="number" dense autofocus counter @keyup.enter="scope.set" />'
        else:
            input_tag = '<q-input v-model="scope.value" dense autofocus counter @keyup.enter="scope.set" />'

        # Note: We use {{{{ }}}} to output {{ }} in the final Vue template through Python's f-string
        body_html += f"""
        <q-td key="{field_name}" :props="props">
            {{{{ props.row.{field_name} }}}}
            <q-popup-edit v-model="props.row.{field_name}" v-slot="scope"
                @update:model-value="() => $parent.$emit('rename', props.row)"
            >
                {input_tag}
            </q-popup-edit>
        </q-td>
        """

    body_html += "</q-tr>"

    # 3. Add the UI slots
    with table.add_slot("header"):
        with table.row():
            table.header().props("auto-width")  # Space for the delete button
            for col in table_columns:
                with table.header(col["name"]):
                    ui.label(col["label"])

    table.add_slot("body", body_html)

    # 4. API Handlers
    async def load_data():
        try:
            async with httpx.AsyncClient() as client:
                res = await client.get(api_url)
                res.raise_for_status()
                table.rows = res.json()
                table.update()
        except Exception as e:
            ui.notify(f"Failed to load data: {e}", color="negative")

    async def add_row() -> None:
        # Generate default data payload based on column types
        new_data = {}
        for f in fields:
            new_data[f["name"]] = f.get("default", "" if f.get("type") == "text" else 0)

        print("Adding new row with data:", new_data)
        try:
            async with httpx.AsyncClient() as client:
                res = await client.post(api_url, json=new_data)
                res.raise_for_status()
                created_row = res.json()
                table.rows.append(created_row)
                ui.notify(
                    f'Added row with ID {created_row.get("id")}', color="positive"
                )
                table.update()
        except Exception as e:
            ui.notify(f"Failed to create: {e}", color="negative")

    async def rename(e: events.GenericEventArguments) -> None:
        row_id = e.args["id"]
        try:
            async with httpx.AsyncClient() as client:
                res = await client.put(f"{api_url}/{row_id}", json=e.args)
                res.raise_for_status()
                for row in table.rows:
                    if row["id"] == row_id:
                        row.update(e.args)
                ui.notify(f"Updated row {row_id}", color="info")
                table.update()
        except Exception as e:
            ui.notify(f"Failed to update: {e}", color="negative")
            await load_data()  # Re-fetch to undo UI change on failure

    async def delete(e: events.GenericEventArguments) -> None:
        row_id = e.args["id"]
        try:
            async with httpx.AsyncClient() as client:
                res = await client.delete(f"{api_url}/{row_id}")
                res.raise_for_status()
                table.rows[:] = [row for row in table.rows if row["id"] != row_id]
                ui.notify(f"Deleted row {row_id}")
                table.update()
        except Exception as e:
            ui.notify(f"Failed to delete: {e}", color="negative")

    # Add the "Add Row" button to the bottom slot
    with table.add_slot("bottom-row"):
        with table.cell().props(f"colspan={len(fields) + 1}"):
            ui.button("Add row", icon="add", color="accent", on_click=add_row).classes(
                "w-full"
            )

    # Bind events
    table.on("rename", rename)
    table.on("delete", delete)

    # Use a timer to trigger the initial data load right after the UI renders
    ui.timer(0, load_data, once=True)

    return table


async def sent_command(api_url: str, command: str | None = None):
    async with httpx.AsyncClient() as client:
        res = await client.post(str(api_url), json={"command": command})
        res.raise_for_status()
        return res.json()


@ui.page("/")
async def page():
    page_header_title("Cyclus Manager")

    ERGOMETERS_CONFIG = json.loads(os.getenv("ERGOMETERS_CONFIG", "{}"))
    legend_state = {}

    def ensure_legend_state(ergo_key: str) -> dict:
        if ergo_key not in legend_state:
            legend_state[ergo_key] = dict(DEFAULT_LEGEND_SELECTED)
        return legend_state[ergo_key]

    ui.label(str(live_data))

    def build_chart_options(ergo_key: str) -> dict:
        data_distance = list(
            zip(live_data[ergo_key]["time"], live_data[ergo_key]["distance"])
        )
        data_crank_rotations = list(
            zip(live_data[ergo_key]["time"], live_data[ergo_key]["crank_rotations"])
        )
        data_work = list(
            zip(live_data[ergo_key]["time"], live_data[ergo_key]["work"])
        )
        data_cadence = list(
            zip(live_data[ergo_key]["time"], live_data[ergo_key]["cadence"])
        )
        data_heart_rate = list(
            zip(live_data[ergo_key]["time"], live_data[ergo_key]["heart_rate"])
        )
        data_speed = list(
            zip(live_data[ergo_key]["time"], live_data[ergo_key]["speed"])
        )
        data_transmission = list(
            zip(live_data[ergo_key]["time"], live_data[ergo_key]["transmission"])
        )
        data_pedal_force = list(
            zip(live_data[ergo_key]["time"], live_data[ergo_key]["pedal_force"])
        )
        data_power = list(
            zip(live_data[ergo_key]["time"], live_data[ergo_key]["power"])
        )
        data_inclination = list(
            zip(live_data[ergo_key]["time"], live_data[ergo_key]["inclination"])
        )
        return {
            "xAxis": {"type": "time"},
            "yAxis": {"type": "value"},
            "legend": {
                "textStyle": {"color": "gray"},
                "selected": ensure_legend_state(ergo_key),
            },
            "series": [
                {
                    "type": "line",
                    "name": "Distance",
                    "symbol": "diamond",
                    "showSymbol": False,
                    "data": data_distance,
                },
                {
                    "type": "line",
                    "name": "Crank Rotations",
                    "symbol": "diamond",
                    "showSymbol": False,
                    "data": data_crank_rotations,
                },
                {
                    "type": "line",
                    "name": "Work",
                    "symbol": "diamond",                   
                    "showSymbol": False,
                    "data": data_work,
                },
                {
                    "type": "line",
                    "name": "Cadence",
                    "symbol": "diamond",
                    "showSymbol": False,
                    "data": data_cadence,
                },
                {
                    "type": "line",
                    "name": "Heart Rate",
                    "symbol": "diamond",
                    "showSymbol": False,
                    "data": data_heart_rate,
                },
                {
                    "type": "line",
                    "name": "Speed",
                    "symbol": "diamond",
                    "showSymbol": False,
                    "data": data_speed,
                },
                {
                    "type": "line",
                    "name": "Transmission",
                    "symbol": "diamond",
                    "showSymbol": False,
                    "data": data_transmission,
                },
                {
                    "type": "line",
                    "name": "Pedal Force",
                    "symbol": "diamond",
                    "showSymbol": False,
                    "data": data_pedal_force,
                },
                {
                    "type": "line",
                    "name": "Power",
                    "symbol": "diamond",
                    "showSymbol": False,
                    "data": data_power,
                },
                {
                    "type": "line",
                    "name": "Inclination",
                    "symbol": "diamond",
                    "showSymbol": False,
                    "data": data_inclination,
                },
            ],
        }

    chart_state = {}
    with ui.row().classes("w-full"):
        async with httpx.AsyncClient() as client:
            res = await client.get(str("http://api:8000/bicycles"))
            res.raise_for_status()
            bicycle_options = {}
            for bicycle in res.json():
                bicycle_options[bicycle["id"]] = f"{bicycle['label']}"

        async with httpx.AsyncClient() as client:
            res = await client.get(str("http://api:8000/users"))
            res.raise_for_status()
            athlete_options = {}
            for athlete in res.json():
                athlete_options[athlete["id"]] = (
                    f"{athlete['first_name']} {athlete['last_name']}"
                )

        for key, value in ERGOMETERS_CONFIG.items():
            with ui.card().classes("flex-1"):
                with ui.row().classes("w-full items-center"):
                    ui.label(f"{key}").style("font-size: 24px;")

                    async def set_time(k=key):
                        result = await sent_command(
                            f"http://api:8000/api/ergometers/{k}/time"
                        )
                        ui.notify(str(result))

                    ui.space()
                    ui.button("Set time", on_click=set_time)

                with ui.row().classes("w-full items-center"):

                    athlete_select = ui.select(
                        athlete_options, label="Athlete", value=1
                    )

                    bicycle_select = ui.select(bicycle_options, label="Bike", value=1)

                    async def setup(
                        k=key,
                        athlete_select=athlete_select,
                        bicycle_select=bicycle_select,
                    ):
                        result = await sent_command(
                            f"http://api:8000/api/ergometers/{k}/setup?user_id={athlete_select.value}&bicycle_id={bicycle_select.value}"
                        )
                        ui.notify(str(result))

                    ui.space()
                    ui.button("Set up", on_click=setup)

                echart = ui.echart(build_chart_options(key))

                def on_legend_select_changed(
                    e: events.GenericEventArguments, ergo_key=key
                ) -> None:
                    if not isinstance(e.args, dict):
                        return

                    selected = e.args.get("selected")
                    if not isinstance(selected, dict):
                        return

                    current = ensure_legend_state(ergo_key)
                    current.update(
                        {
                            str(name): bool(is_visible)
                            for name, is_visible in selected.items()
                        }
                    )
                    print(
                        f"[legend] {ergo_key} updated selection: {json.dumps(current, sort_keys=True)}"
                    )

                echart.on("chart:legendselectchanged", on_legend_select_changed)
                chart_state[key] = {
                    "chart": echart,
                    "rendered_version": data_version[key],
                }

    def refresh_charts() -> None:
        for ergo_key, state in chart_state.items():
            if state["rendered_version"] == data_version[ergo_key]:
                continue

            print(
                f"[refresh] {ergo_key} data_version={data_version[ergo_key]} legend={json.dumps(ensure_legend_state(ergo_key), sort_keys=True)}"
            )
            chart = state["chart"]
            new_options = build_chart_options(ergo_key)
            chart.options.update(new_options)
            chart.update()
            state["rendered_version"] = data_version[ergo_key]

    # Throttle redraws to at most one update per second, while still reacting to fresh data.
    ui.timer(1.0, refresh_charts)


@ui.page("/settings")
def settings_page():
    page_header_title("Settings")
    ui.label("Add Cyclus").style(
        "font-size: 18px; font-weight: bold; margin-bottom: 10px;"
    )
    ui.input("Label").props("required")
    ui.input("IP").props("required")
    ui.button("Add Cyclus").style("margin-top: 10px;")


@ui.page("/athletes")
def athletes_page():
    page_header_title("Athletes")

    user_fields = [
        {"name": "first_name", "label": "First Name", "type": "text", "default": "New"},
        {"name": "last_name", "label": "Last Name", "type": "text", "default": "New"},
        {
            "name": "date_of_birth",
            "label": "Date of Birth",
            "type": "date",
            "default": "1990-01-01",
        },
        {"name": "gender", "label": "Gender", "type": "number", "default": 0},
        {
            "name": "body_weight_kg",
            "label": "Body Weight (kg)",
            "type": "number",
            "default": 0,
        },
        {
            "name": "body_height_m",
            "label": "Body Height (m)",
            "type": "number",
            "default": 0,
        },
        {
            "name": "drag_area_m2",
            "label": "Drag Area (m²)",
            "type": "number",
            "default": 0.33,
        },
        {
            "name": "drag_coefficient",
            "label": "Drag Coefficient",
            "type": "number",
            "default": 0.5,
        },
    ]

    create_api_table(api_url="http://api:8000/users", fields=user_fields)


@ui.page("/bikes")
def bikes_page():
    page_header_title("Bikes")
    user_fields = [
        {"name": "label", "label": "Label", "type": "text", "default": "New Bike"},
        {
            "name": "wheel_size_m",
            "label": "Wheel Size (m)",
            "type": "number",
            "default": 0.68,
        },
        {
            "name": "crank_length_m",
            "label": "Crank Length (m)",
            "type": "number",
            "default": 0,
        },
        {"name": "weight_kg", "label": "Weight (kg)", "type": "number", "default": 6.8},
        {
            "name": "chainring_size",
            "label": "Chainring Size",
            "type": "number",
            "default": 0,
        },
        {
            "name": "sprocket_size",
            "label": "Sprocket Size",
            "type": "number",
            "default": 12,
        },
    ]

    create_api_table(api_url="http://api:8000/bicycles", fields=user_fields)


@ui.page("/training_plans")
async def training_plans_page():
    page_header_title("Training Plans")

    async def fetch_training_plans():
        async with httpx.AsyncClient() as client:
            response = await client.get("http://api:8000/training_plans")
            return response.json()

    training_plans_data = await fetch_training_plans()
    columns = [
        {"name": "id", "label": "ID", "field": "id", "sortable": True},
        {"name": "label", "label": "Name", "field": "label", "sortable": True},
        {
            "name": "duration_s",
            "label": "Duration (s)",
            "field": "duration_s",
            "sortable": True,
        },
        {"name": "file_path", "label": "File Path", "field": "file_path"},
    ]

    training_plans = ui.table(columns=columns, rows=training_plans_data)


@ui.page("/training_sessions")
async def training_sessions_page():
    page_header_title("Training Sessions")

    async def fetch_training_sessions():
        async with httpx.AsyncClient() as client:
            response = await client.get("http://api:8000/training_sessions")
            return response.json()

    training_sessions_data = await fetch_training_sessions()
    columns = [
        {"name": "id", "label": "ID", "field": "id", "sortable": True},
        {"name": "user_id", "label": "User", "field": "user_id", "sortable": True},
        {
            "name": "bicycle_id",
            "label": "Bicycle",
            "field": "bicycle_id",
            "sortable": True,
        },
        {
            "name": "training_plan_id",
            "label": "Training Plan",
            "field": "training_plan_id",
            "sortable": True,
        },
        {"name": "date", "label": "Date", "field": "date", "sortable": True},
        {
            "name": "duration_s",
            "label": "Duration (s)",
            "field": "duration_s",
            "sortable": True,
        },
        {
            "name": "distance_km",
            "label": "Distance (km)",
            "field": "distance_km",
            "sortable": True,
        },
        {
            "name": "average_speed_kmh",
            "label": "Average Speed (km/h)",
            "field": "average_speed_kmh",
            "sortable": True,
        },
        {
            "name": "average_power_w",
            "label": "Average Power (W)",
            "field": "average_power_w",
            "sortable": True,
        },
        {"name": "file_path", "label": "File Path", "field": "file_path"},
        {"name": "action", "label": "Action", "align": "center"},
    ]

    training_sessions = ui.table(columns=columns, rows=training_sessions_data)
    with training_sessions.add_slot("body-cell-action"):
        with training_sessions.cell("action"):
            ui.button("View", color="primary").props("flat").on(
                "click",
                js_handler="() => emit(props.row.id)",
                handler=lambda e: ui.notify(e.args),
            )


ui.run(favicon="🚲")
