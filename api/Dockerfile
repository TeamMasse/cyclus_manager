FROM python:latest

WORKDIR /api

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade -r requirements.txt

COPY main.py .

CMD ["fastapi", "run", "main.py", "--port", "8000"]