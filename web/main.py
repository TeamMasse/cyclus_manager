#import plotly.graph_objects as go
from nicegui import app, ui
import httpx

app.colors(primary="#1e1e1e",secondary = '#26a69a',accent = '#9c27b0',dark = "#1e1e1e",dark_page = '#121212',positive = '#21ba45',negative = '#c10015',info = '#31ccec',warning = '#f2c037')

def page_header_title(title):
    ui.dark_mode(True)
    ui.page_title('Cyclus Manager')
    with ui.header():
        ui.button(on_click=lambda: left_drawer.toggle(), icon='menu')
        ui.label(title).style('font-size: 24px;')
        
    with ui.left_drawer(fixed=True).props('width=100') as left_drawer:
        ui.link('Home', '/').style('display: block; margin-bottom: 5px; color: white; text-decoration-line: none')
        ui.link('Settings', '/settings').style('display: block; margin-bottom: 5px; color: white; text-decoration-line: none')
        ui.link('Athletes', '/athletes').style('display: block; margin-bottom: 5px; color: white; text-decoration-line: none')
        ui.link('Bikes', '/bikes').style('display: block; margin-bottom: 5px; color: white; text-decoration-line: none')
        ui.link('Training Plans', '/training_plans').style('display: block; margin-bottom: 5px; color: white; text-decoration-line: none')
        ui.link('Training Sessions', '/training_sessions').style('display: block; margin-bottom: 5px; color: white; text-decoration-line: none')

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
            'yaxis': {'gridcolor': 'black'}
        },
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
async def athletes_page():
    page_header_title('Athletes')
    async def fetch_athletes():
        async with httpx.AsyncClient() as client:
            response = await client.get('http://api:8000/users')           
            return response.json()
        
    async def add_athlete():
        new_athlete = {
            "first_name": first_name_input.value,
            "last_name": last_name_input.value,
            "date_of_birth": date_of_birth_input.value,
            "gender": gender_input.value if gender_input.value else 0,
            "body_weight_kg": float(body_weight_input.value),
            "body_height_m": float(body_height_input.value),
            "drag_area_m2": float(drag_area_input.value),
            "drag_coefficient": float(drag_coefficient_input.value),
        }
        async with httpx.AsyncClient() as client:
            await client.post('http://api:8000/users', json=new_athlete)
        atheltes.rows = await fetch_athletes()
        atheltes.update()
        
    athletes_data = await fetch_athletes()
    columns = [
        {'name': 'id', 'label': 'ID', 'field': 'id', 'sortable': True},
        {'name': 'first_name', 'label': 'First Name', 'field': 'first_name', 'sortable': True},
        {'name': 'last_name', 'label': 'Last Name', 'field': 'last_name', 'sortable': True},
        {'name': 'date_of_birth', 'label': 'Date of Birth', 'field': 'date_of_birth', 'sortable': True},
        {'name': 'gender', 'label': 'Gender', 'field': 'gender', 'sortable': True},
        {'name': 'body_weight_kg', 'label': 'Body Weight (kg)', 'field': 'body_weight_kg', 'sortable': True},
        {'name': 'body_height_m', 'label': 'Body Height (m)', 'field': 'body_height_m', 'sortable': True},
        {'name': 'drag_area_m2', 'label': 'Drag area (m²)', 'field': 'drag_area_m2'},
        {'name': 'drag_coefficient', 'label': 'Drag coefficient', 'field': 'drag_coefficient'},     
    ]

    atheltes = ui.table(columns=columns, rows=athletes_data)
    
    ui.label('Add Athlete').style('font-size: 18px; font-weight: bold; margin-bottom: 10px;')
    with ui.row():
        first_name_input = ui.input('First Name')
        last_name_input = ui.input('Last Name')
        date_of_birth_input = ui.date_input('Date of Birth')
        gender_input = ui.input('Gender')
        body_weight_input = ui.input('Body Weight (kg)')
        body_height_input = ui.input('Body Height (m)')
        drag_area_input = ui.input('Drag Area (m²)')
        drag_coefficient_input = ui.input('Drag Coefficient')
    ui.button('Add Athlete', on_click=add_athlete).style('margin-top: 10px;')

@ui.page('/bikes')
async def bikes_page():
    page_header_title('Bikes')
    async def fetch_bikes():
        async with httpx.AsyncClient() as client:
            response = await client.get('http://api:8000/bicycles')           
            return response.json()
        
    async def add_bike():
        print('Adding bike...')
        new_bike = {
            "label": label_input.value,
            "wheel_size_m": float(wheel_size_input.value) if wheel_size_input.value else 0.68,
            "crank_length_m": float(crank_length_input.value),
            "weight_kg": float(weight_input.value) if weight_input.value else 6.8,
            "chainring_size": int(chainring_size_input.value),
            "sprocket_size": int(sprocket_size_input.value) if sprocket_size_input.value else 12,
        }
        print('New bike data:', new_bike)
        async with httpx.AsyncClient() as client:
            await client.post('http://api:8000/bicycles', json=new_bike)
        bikes.rows = await fetch_bikes()
        bikes.update()     
    
    bikes_data = await fetch_bikes()
    columns = [
        {'name': 'id', 'label': 'ID', 'field': 'id', 'sortable': True},
        {'name': 'label', 'label': 'Name', 'field': 'label', 'sortable': True},
        {'name': 'wheel_size_m', 'label': 'Wheel size (m)', 'field': 'wheel_size_m', 'sortable': True},
        {'name': 'crank_length_m', 'label': 'Crank length (m)', 'field': 'crank_length_m', 'sortable': True},
        {'name': 'weight_kg', 'label': 'Weight (kg)', 'field': 'weight_kg', 'sortable': True},
        {'name': 'chainring_size', 'label': 'Chainring size', 'field': 'chainring_size', 'sortable': True},
        {'name': 'sprocket_size', 'label': 'Sprocket size', 'field': 'sprocket_size', 'sortable': True},      
    ]
    
    bikes = ui.table(columns=columns, rows=bikes_data)
    
    ui.label('Add Bike').style('font-size: 18px; font-weight: bold; margin-bottom: 10px;')
    with ui.row():
        label_input = ui.input('Label')
        wheel_size_input = ui.input('Wheel Size (m)')
        crank_length_input = ui.input('Crank Length (m)')
        weight_input = ui.input('Weight (kg)')
        chainring_size_input = ui.input('Chainring Size')
        sprocket_size_input = ui.input('Sprocket Size')
    ui.button('Add Bike', on_click=add_bike).style('margin-top: 10px;')
    
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
        
ui.run()