#!/bin/bash
set -e

echo "🔍 Validating environment variables..."
python /usr/local/bin/validate_env.py

echo "🚀 Starting application..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8001 --workers 1
