FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y gcc default-libmysqlclient-dev libpq-dev curl ca-certificates && rm -rf /var/lib/apt/lists/*

# Tải sẵn chứng chỉ CA bundle chính thức của AWS (DocumentDB & RDS)
RUN mkdir -p /app/certs && \
    curl -sS https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem -o /app/certs/global-bundle.pem || true

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
