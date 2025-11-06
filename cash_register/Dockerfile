FROM python:3.11-slim
WORKDIR /app

# Install PostgreSQL client tools (for pg_isready)
RUN apt-get update && apt-get install -y postgresql-client && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py wait-for-postgres.sh ./
RUN chmod +x wait-for-postgres.sh

COPY mvc_app/ mvc_app/
COPY log.cfg .

EXPOSE 5000
CMD ["./wait-for-postgres.sh", "python", "app.py"]