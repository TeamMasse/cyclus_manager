#import plotly.graph_objects as go
from nicegui import events, app, ui
import httpx

app.colors(primary="#575757",secondary = '#26a69a',accent = "#2732b0",dark = "#1e1e1e",dark_page = '#121212',positive = '#21ba45',negative = '#c10015',info = '#31ccec',warning = "#ff0000")

def page_header_title(title):
    """
    Creates a header for the page.
    
    :param title: The title for the page
    """
    ui.dark_mode(True)
    ui.page_title('Cyclus Manager')
    
    # Header with toggle button for the left drawer
    with ui.header():
        ui.button(on_click=lambda: left_drawer.toggle(), icon='menu')
        ui.label(title).style('font-size: 24px;')
        
    # Left drawer with navigation links
    with ui.left_drawer(fixed=True).props('width=100') as left_drawer:
        ui.link('Home', '/').style('display: block; margin-bottom: 5px; color: white; text-decoration-line: none')
        ui.link('Settings', '/settings').style('display: block; margin-bottom: 5px; color: white; text-decoration-line: none')
        ui.link('Athletes', '/athletes').style('display: block; margin-bottom: 5px; color: white; text-decoration-line: none')
        ui.link('Bikes', '/bikes').style('display: block; margin-bottom: 5px; color: white; text-decoration-line: none')
        ui.link('Training Plans', '/training_plans').style('display: block; margin-bottom: 5px; color: white; text-decoration-line: none')
        ui.link('Training Sessions', '/training_sessions').style('display: block; margin-bottom: 5px; color: white; text-decoration-line: none')

def create_api_table(api_url: str, fields: list):
    """
    Creates a NiceGUI editable table linked to a REST API.
    
    :param api_url: The base endpoint for the resource (e.g., 'http://localhost:8000/api/athletes')
    :param fields: List of dicts defining columns, e.g., [{'name': 'age', 'label': 'Age', 'type': 'number'}]
    """
    
    # 1. Transform the provided fields into NiceGUI's column format
    table_columns = []
    for f in fields:
        table_columns.append({
            'name': f['name'],
            'label': f['label'],
            'field': f['name'],
            'align': f.get('align', 'left')
        })

    # Initialize the table empty
    table = ui.table(columns=table_columns, rows=[], row_key='id').classes('w-full')

    # 2. Dynamically build the Vue Template for the table body
    body_html = '''
    <q-tr :props="props">
        <q-td auto-width>
            <q-btn size="sm" color="warning" round dense icon="delete"
                @click="() => $parent.$emit('delete', props.row)"
            />
        </q-td>
    '''
    
    for f in fields:
        field_name = f['name']
        col_type = f.get('type', 'text')
        
        # Use different Vue inputs based on data type
        if col_type == 'number':
            input_tag = '<q-input v-model.number="scope.value" type="number" dense autofocus counter @keyup.enter="scope.set" />'
        else:
            input_tag = '<q-input v-model="scope.value" dense autofocus counter @keyup.enter="scope.set" />'

        # Note: We use {{{{ }}}} to output {{ }} in the final Vue template through Python's f-string
        body_html += f'''
        <q-td key="{field_name}" :props="props">
            {{{{ props.row.{field_name} }}}}
            <q-popup-edit v-model="props.row.{field_name}" v-slot="scope"
                @update:model-value="() => $parent.$emit('rename', props.row)"
            >
                {input_tag}
            </q-popup-edit>
        </q-td>
        '''
        
    body_html += '</q-tr>'

    # 3. Add the UI slots
    with table.add_slot('header'):
        with table.row():
            table.header().props('auto-width') # Space for the delete button
            for col in table_columns:
                with table.header(col['name']):
                    ui.label(col['label'])
                    
    table.add_slot('body', body_html)

    # 4. API Handlers
    async def load_data():
        try:
            async with httpx.AsyncClient() as client:
                res = await client.get(api_url)
                res.raise_for_status()
                table.rows = res.json()
                table.update()
        except Exception as e:
            ui.notify(f'Failed to load data: {e}', color='negative')

    async def add_row() -> None:
        # Generate default data payload based on column types
        new_data = {}
        for f in fields:
            new_data[f['name']] = f.get('default', '' if f.get('type') == 'text' else 0)
        
        print('Adding new row with data:', new_data)
        try:
            async with httpx.AsyncClient() as client:
                res = await client.post(api_url, json=new_data)
                res.raise_for_status()
                created_row = res.json() 
                table.rows.append(created_row)
                ui.notify(f'Added row with ID {created_row.get("id")}', color='positive')
                table.update()
        except Exception as e:
            ui.notify(f'Failed to create: {e}', color='negative')

    async def rename(e: events.GenericEventArguments) -> None:
        row_id = e.args['id']
        try:
            async with httpx.AsyncClient() as client:
                res = await client.put(f"{api_url}/{row_id}", json=e.args)
                res.raise_for_status()
                for row in table.rows:
                    if row['id'] == row_id:
                        row.update(e.args)
                ui.notify(f'Updated row {row_id}', color='info')
                table.update()
        except Exception as e:
            ui.notify(f'Failed to update: {e}', color='negative')
            await load_data() # Re-fetch to undo UI change on failure

    async def delete(e: events.GenericEventArguments) -> None:
        row_id = e.args['id']
        try:
            async with httpx.AsyncClient() as client:
                res = await client.delete(f"{api_url}/{row_id}")
                res.raise_for_status()
                table.rows[:] = [row for row in table.rows if row['id'] != row_id]
                ui.notify(f'Deleted row {row_id}')
                table.update()
        except Exception as e:
            ui.notify(f'Failed to delete: {e}', color='negative')

    # Add the "Add Row" button to the bottom slot
    with table.add_slot('bottom-row'):
        with table.cell().props(f'colspan={len(fields) + 1}'):
            ui.button('Add row', icon='add', color='accent', on_click=add_row).classes('w-full')

    # Bind events
    table.on('rename', rename)
    table.on('delete', delete)

    # Use a timer to trigger the initial data load right after the UI renders
    ui.timer(0, load_data, once=True)

    return table

@ui.page('/')
def page():
    page_header_title('Cyclus Manager')
    
    ui.label('Hello World!')
    fig = {
        'data': [
            {
                'type': 'scatter',
                'name': 'Trace 1',
                'x': [1,2,3,4],
                'y': [2,5,6,1],
            },
            {
                'type': 'scatter',
                'name': 'Trace 2',
                'x': [1,2,3,4],
                'y': [21,5,-5,1],
            },
        ],
        'layout': {
            'margin': {'l': 15, 'r': 15, 't': 0, 'b': 15},
            'plot_bgcolor': "#5e6c80",
            'showlegend': 'False',
            'xaxis': {'gridcolor': 'white'},
            'yaxis': {'gridcolor': 'black'},
        }
    }
    with ui.row():
        ui.plotly(fig).classes('w-80 h-full')
        ui.plotly(fig).classes('w-80 h-full')
        ui.plotly(fig).classes('w-80 h-full')
        


@ui.page('/settings')
def settings_page():
    page_header_title('Settings')
    ui.label('Add Cyclus').style('font-size: 18px; font-weight: bold; margin-bottom: 10px;')
    ui.input('Label').props('required')
    ui.input('IP').props('required')
    ui.button('Add Cyclus').style('margin-top: 10px;')
    
@ui.page('/athletes')
def athletes_page():
    page_header_title('Athletes')
    
    user_fields = [
        {'name': 'first_name', 'label': 'First Name', 'type': 'text', 'default': 'New'},
        {'name': 'last_name', 'label': 'Last Name', 'type': 'text', 'default': 'New'},
        {'name': 'date_of_birth', 'label': 'Date of Birth', 'type': 'date', 'default': '1990-01-01'},
        {'name': 'gender', 'label': 'Gender', 'type': 'number', 'default': 0},
        {'name': 'body_weight_kg', 'label': 'Body Weight (kg)', 'type': 'number', 'default': 0},
        {'name': 'body_height_m', 'label': 'Body Height (m)', 'type': 'number', 'default': 0},
        {'name': 'drag_area_m2', 'label': 'Drag Area (m²)', 'type': 'number', 'default': 0.33},
        {'name': 'drag_coefficient', 'label': 'Drag Coefficient', 'type': 'number', 'default': 0.5},
    ]
    
    create_api_table(
        api_url="http://api:8000/users", 
        fields=user_fields
    )

@ui.page('/bikes')
def bikes_page():
    page_header_title('Bikes')
    user_fields = [
        {'name': 'label', 'label': 'Label', 'type': 'text', 'default': 'New Bike'},
        {'name': 'wheel_size_m', 'label': 'Wheel Size (m)', 'type': 'number', 'default': 0.68},
        {'name': 'crank_length_m', 'label': 'Crank Length (m)', 'type': 'number', 'default': 0},
        {'name': 'weight_kg', 'label': 'Weight (kg)', 'type': 'number', 'default': 6.8},
        {'name': 'chainring_size', 'label': 'Chainring Size', 'type': 'number', 'default': 0},
        {'name': 'sprocket_size', 'label': 'Sprocket Size', 'type': 'number', 'default': 12},
    ]
    
    create_api_table(
        api_url="http://api:8000/bicycles", 
        fields=user_fields
    )
    
@ui.page('/training_plans')
async def training_plans_page():
    page_header_title('Training Plans')
    async def fetch_training_plans():
        async with httpx.AsyncClient() as client:
            response = await client.get('http://api:8000/training_plans')
            return response.json()   
    
    training_plans_data = await fetch_training_plans()
    columns = [
        {'name': 'id', 'label': 'ID', 'field': 'id', 'sortable': True},
        {'name': 'label', 'label': 'Name', 'field': 'label', 'sortable': True},
        {'name': 'duration_s', 'label': 'Duration (s)', 'field': 'duration_s', 'sortable': True},
        {'name': 'file_path', 'label': 'File Path', 'field': 'file_path'},
    ]
    
    training_plans = ui.table(columns=columns, rows=training_plans_data)

@ui.page('/training_sessions')
async def training_sessions_page():
    page_header_title('Training Sessions')
    async def fetch_training_sessions():
        async with httpx.AsyncClient() as client:
            response = await client.get('http://api:8000/training_sessions')
            return response.json()   
    
    training_sessions_data = await fetch_training_sessions()
    columns = [
        {'name': 'id', 'label': 'ID', 'field': 'id', 'sortable': True},
        {'name': 'user_id', 'label': 'User', 'field': 'user_id', 'sortable': True},
        {'name': 'bicycle_id', 'label': 'Bicycle', 'field': 'bicycle_id', 'sortable': True},
        {'name': 'training_plan_id', 'label': 'Training Plan', 'field': 'training_plan_id', 'sortable': True},
        {'name': 'date', 'label': 'Date', 'field': 'date', 'sortable': True},
        {'name': 'duration_s', 'label': 'Duration (s)', 'field': 'duration_s', 'sortable': True},
        {'name': 'distance_km', 'label': 'Distance (km)', 'field': 'distance_km', 'sortable': True},
        {'name': 'average_speed_kmh', 'label': 'Average Speed (km/h)', 'field': 'average_speed_kmh', 'sortable': True},
        {'name': 'average_power_w', 'label': 'Average Power (W)', 'field': 'average_power_w', 'sortable': True},
        {'name': 'file_path', 'label': 'File Path', 'field': 'file_path'},
        {'name': 'action', 'label': 'Action', 'align': 'center'},
    ]
    
    training_sessions = ui.table(columns=columns, rows=training_sessions_data)
    with training_sessions.add_slot('body-cell-action'):
        with training_sessions.cell('action'):
            ui.button('View', color='primary').props('flat').on('click', js_handler='() => emit(props.row.id)',
            handler=lambda e: ui.notify(e.args),)
        
ui.run(favicon="🚲")