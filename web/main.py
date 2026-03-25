import time
from nicegui import Event, app, ui
import httpx
import asyncio

def page_header_title(title):
    ui.page_title('Cyclus Manager')
    with ui.header().style('background-color: #333; color: white; padding: 10px;'):
        ui.button(on_click=lambda: left_drawer.toggle(), icon='menu').props('flat color=white')
        ui.label(title).style('font-size: 24px; font-weight: bold;')
        
    with ui.left_drawer(fixed=True).props('width=100').style('background-color: #f4f4f4; padding: 20px;') as left_drawer:
        ui.link('Home', '/').style('display: block; margin-bottom: 5px; color: white;')
        ui.link('Settings', '/settings').style('display: block; margin-bottom: 5px; color: white;')
        ui.link('Athletes', '/athletes').style('display: block; margin-bottom: 5px; color: white;')
        ui.link('Bikes', '/bikes').style('display: block; margin-bottom: 5px; color: white;')


@ui.page('/')
def page():
    page_header_title('Cyclus Manager')
    
    ui.label('Hello World!')

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
            "gender": gender_input.value,
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
        {'name': 'id', 'label': 'ID', 'field': 'id'},
        {'name': 'first_name', 'label': 'First Name', 'field': 'first_name'},
        {'name': 'last_name', 'label': 'Last Name', 'field': 'last_name'},
        {'name': 'date_of_birth', 'label': 'Date of Birth', 'field': 'date_of_birth'},
        {'name': 'gender', 'label': 'Gender', 'field': 'gender'},
        {'name': 'body_weight_kg', 'label': 'Body Weight (kg)', 'field': 'body_weight_kg'},
        {'name': 'body_height_m', 'label': 'Body Height (m)', 'field': 'body_height_m'},
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
        {'name': 'id', 'label': 'ID', 'field': 'id'},
        {'name': 'label', 'label': 'Name', 'field': 'label'},
        {'name': 'wheel_size_m', 'label': 'Wheel size (m)', 'field': 'wheel_size_m'},
        {'name': 'crank_length_m', 'label': 'Crank length (m)', 'field': 'crank_length_m'},
        {'name': 'weight_kg', 'label': 'Weight (kg)', 'field': 'weight_kg'},
        {'name': 'chainring_size', 'label': 'Chainring size', 'field': 'chainring_size'},
        {'name': 'sprocket_size', 'label': 'Sprocket size', 'field': 'sprocket_size'},      
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

ui.run()