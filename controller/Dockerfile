FROM python:latest

WORKDIR /controller

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade -r requirements.txt

COPY main.py .

CMD ["python", "./app.py"]