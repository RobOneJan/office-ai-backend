FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Cloud Run erwartet diesen Port
EXPOSE 8080

# CMD nutzt Cloud Run PORT-Variable
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
