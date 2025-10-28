#!/bin/sh
# wait-for-postgres.sh
set -e

host="db"
port=5432

echo "⏳ Waiting for PostgreSQL at $host:$port..."

until pg_isready -h "$host" -p "$port" -q; do
  echo "Postgres is unavailable - sleeping"
  sleep 1
done

echo "✅ PostgreSQL is up - executing command"
exec "$@"
